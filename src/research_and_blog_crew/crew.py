"""Research & blog crew orchestration.

A 7-agent pipeline that turns a topic into a research dossier, a long-form
report, and a publish-ready blog post. Designed to be imported by both the
CLI entry point (main.py) and the FastAPI service (api/services/crew_runner.py).
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable

from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from crewai.agents.agent_builder.base_agent import BaseAgent

from research_and_blog_crew.tools.custom_tool import CitationFormatterTool


# ---- Rate-limit retry wrapper ---------------------------------------------
# Groq's free tier enforces per-minute token limits. When we hit them, litellm
# raises a BadRequestError with a "Please try again in Xs" hint. This wrapper
# catches that and retries with the recommended sleep, so the crew self-heals
# on transient rate limits.

_DEFAULT_RETRY_EXCEPTIONS = (
    "RateLimitError",
    "BadRequestError",  # Groq returns BadRequestError for rate_limit_exceeded
    "ServiceUnavailableError",
    "Timeout",
)


def _is_rate_limit_error(exc: BaseException) -> tuple[bool, float]:
    """Return (is_rate_limit, sleep_seconds) for a given exception."""
    msg = str(exc)
    if "rate_limit_exceeded" not in msg and "RateLimitError" not in msg:
        return False, 0.0
    # Parse "Please try again in 28.45s" or similar
    import re
    m = re.search(r"try again in (\d+(?:\.\d+)?)s", msg)
    if m:
        return True, float(m.group(1)) + 1.0  # +1s buffer
    return True, 30.0


def with_rate_limit_retry(fn: Callable[[], Any], max_retries: int = 5) -> Any:
    """Call fn(); on rate-limit errors, sleep and retry up to max_retries times."""
    last_exc: BaseException | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            is_rl, sleep_s = _is_rate_limit_error(exc)
            last_exc = exc
            if not is_rl or attempt == max_retries:
                raise
            time.sleep(sleep_s)
    # Unreachable, but keeps type-checkers happy
    raise last_exc  # type: ignore[misc]


def _get_api_keys() -> list[str]:
    """Collect every configured Groq API key from the environment.

    Primary key comes from GROQ_API_KEY (kept for backward compatibility and
    local-dev simplicity). Additional keys come from GROQ_API_KEYS as a
    comma-separated list. Duplicates and blank entries are removed while
    preserving order. The agent factory hashes the role name to pick a
    deterministic index, so the same agent always uses the same key in a
    given run — this gives us N independent Groq free-tier quotas.
    """
    keys: list[str] = []
    primary = os.environ.get("GROQ_API_KEY", "").strip()
    if primary:
        keys.append(primary)
    extras = os.environ.get("GROQ_API_KEYS", "").strip()
    if extras:
        for k in extras.split(","):
            k = k.strip()
            if k and k not in keys:
                keys.append(k)
    return keys


def _build_llm(role: str = "default") -> LLM:
    """Build the LLM with explicit API key — no env-var magic, no ambiguity.

    Reads MODEL and GROQ_API_KEY[S] directly from os.environ so there is zero
    chance of litellm picking up a stale value from a .env file or a dotenv
    auto-load.  Raises at crew-build time if no key is set so the error is
    obvious in the Render startup logs.

    Per-role model selection: Groq's free tier is more reliable when we route
    tool-using agents to llama-3.3-70b-versatile (12K TPM, strong function
    calling) and text-only agents to llama-4-scout (30K TPM, fastest). This
    keeps the crew well under the per-minute token budget while still letting
    the researcher issue Serper/Scrape tool calls reliably.

    Per-role key selection: agents are deterministically distributed across
    the configured key pool (GROQ_API_KEY, GROQ_API_KEYS=...) so that the 7
    agents don't all hammer a single key's per-minute token budget.
    """
    keys = _get_api_keys()
    if not keys:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. "
            "Add it in the Render Dashboard → service → Environment tab."
        )

    tool_using_roles = {"senior_researcher", "fact_checker"}
    if role in tool_using_roles:
        model = "groq/llama-3.3-70b-versatile"
    else:
        model = os.environ.get(
            "MODEL", "groq/meta-llama/llama-4-scout-17b-16e-instruct"
        )

    # Deterministic key assignment: same role always picks the same key.
    key_index = hash(role) % len(keys)
    api_key = keys[key_index]
    print(f"[crew] role={role!r} model={model!r} key_index={key_index}/{len(keys)}")

    return LLM(model=model, api_key=api_key)


def _build_research_tools() -> list:
    """Tools available to the senior researcher. Serper requires SERPER_API_KEY;
    the scrape tool runs without external dependencies."""
    tools: list = []
    if os.getenv("SERPER_API_KEY"):
        tools.append(SerperDevTool())
    tools.append(ScrapeWebsiteTool())
    return tools


@CrewBase
class ResearchAndBlogCrew:
    """Production research & blog crew with 6 specialized agents."""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # ---------- Agents ----------

    @agent
    def research_planner(self) -> Agent:
        return Agent(
            config=self.agents_config["research_planner"],  # type: ignore[index]
            llm=_build_llm("research_planner"),
            verbose=True,
        )

    @agent
    def senior_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["senior_researcher"],  # type: ignore[index]
            llm=_build_llm("senior_researcher"),
            tools=_build_research_tools() + [CitationFormatterTool()],
            verbose=True,
        )

    @agent
    def fact_checker(self) -> Agent:
        return Agent(
            config=self.agents_config["fact_checker"],  # type: ignore[index]
            llm=_build_llm("fact_checker"),
            verbose=True,
        )

    @agent
    def report_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["report_writer"],  # type: ignore[index]
            llm=_build_llm("report_writer"),
            verbose=True,
        )

    @agent
    def editor(self) -> Agent:
        return Agent(
            config=self.agents_config["editor"],  # type: ignore[index]
            llm=_build_llm("editor"),
            verbose=True,
        )

    @agent
    def blog_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["blog_writer"],  # type: ignore[index]
            llm=_build_llm("blog_writer"),
            verbose=True,
        )

    @agent
    def seo_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config["seo_specialist"],  # type: ignore[index]
            llm=_build_llm("seo_specialist"),
            verbose=True,
        )

    # ---------- Tasks ----------

    @task
    def planning_task(self) -> Task:
        return Task(
            config=self.tasks_config["planning_task"],  # type: ignore[index]
        )

    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config["research_task"],  # type: ignore[index]
            context=[self.planning_task()],
        )

    @task
    def fact_check_task(self) -> Task:
        return Task(
            config=self.tasks_config["fact_check_task"],  # type: ignore[index]
            context=[self.research_task()],
        )

    @task
    def report_task(self) -> Task:
        return Task(
            config=self.tasks_config["report_task"],  # type: ignore[index]
            context=[self.fact_check_task()],
        )

    @task
    def editing_task(self) -> Task:
        return Task(
            config=self.tasks_config["editing_task"],  # type: ignore[index]
            context=[self.report_task()],
        )

    @task
    def blog_writing_task(self) -> Task:
        return Task(
            config=self.tasks_config["blog_writing_task"],  # type: ignore[index]
            context=[self.editing_task()],
        )

    @task
    def seo_task(self) -> Task:
        return Task(
            config=self.tasks_config["seo_task"],  # type: ignore[index]
            context=[self.blog_writing_task()],
        )

    # ---------- Crew ----------

    @crew
    def crew(self) -> Crew:
        """Build the production crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=False,  # memory=True requires OpenAI embeddings; disabled for Groq-only deployments
            cache=True,
        )


def ensure_output_dir(run_id: str, base: str | os.PathLike[str] = "output") -> Path:
    """Create the per-run output directory used by the task output_file paths."""
    p = Path(base) / run_id
    p.mkdir(parents=True, exist_ok=True)
    return p
