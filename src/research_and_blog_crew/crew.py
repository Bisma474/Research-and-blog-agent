"""Research & blog crew orchestration.

A 6-agent pipeline that turns a topic into a research dossier, a long-form
report, and a publish-ready blog post. Designed to be imported by both the
CLI entry point (main.py) and the FastAPI service (api/services/crew_runner.py).
"""

from __future__ import annotations

import os
from pathlib import Path

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from crewai.agents.agent_builder.base_agent import BaseAgent

from research_and_blog_crew.tools.custom_tool import CitationFormatterTool


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
            verbose=True,
        )

    @agent
    def senior_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["senior_researcher"],  # type: ignore[index]
            tools=_build_research_tools() + [CitationFormatterTool()],
            verbose=True,
        )

    @agent
    def fact_checker(self) -> Agent:
        return Agent(
            config=self.agents_config["fact_checker"],  # type: ignore[index]
            verbose=True,
        )

    @agent
    def report_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["report_writer"],  # type: ignore[index]
            verbose=True,
        )

    @agent
    def editor(self) -> Agent:
        return Agent(
            config=self.agents_config["editor"],  # type: ignore[index]
            verbose=True,
        )

    @agent
    def blog_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["blog_writer"],  # type: ignore[index]
            verbose=True,
        )

    @agent
    def seo_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config["seo_specialist"],  # type: ignore[index]
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
            memory=True,
            cache=True,
        )


def ensure_output_dir(run_id: str, base: str | os.PathLike[str] = "output") -> Path:
    """Create the per-run output directory used by the task output_file paths."""
    p = Path(base) / run_id
    p.mkdir(parents=True, exist_ok=True)
    return p
