"""Async wrapper around the CrewAI crew with progress streaming + persistence.

The runner is responsible for:
  * Subscribing to CrewAI events and translating them to lightweight progress
    events that the SSE endpoint can stream.
  * Persisting per-step artifacts (plan, dossier, report, blog, seo) to the
    Run row in the database as soon as each task completes.
  * Running the (blocking) crew.kickoff() call in a worker thread so the
    FastAPI event loop stays responsive.
  * Surfacing failures (with full traceback) on the Run row and the SSE
    channel so the UI can show them.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from queue import Empty, Queue
from typing import Optional

from crewai.events import (
    AgentExecutionCompletedEvent,
    BaseEventListener,
    CrewKickoffCompletedEvent,
    CrewKickoffFailedEvent,
    CrewKickoffStartedEvent,
    TaskCompletedEvent,
)
from sqlmodel import Session

from api import database
from api.config import get_settings
from api.models import Run
from research_and_blog_crew.crew import ResearchAndBlogCrew, ensure_output_dir


# ---- Progress event types ---------------------------------------------------

EVENT_TASK_STARTED = "task_started"
EVENT_TASK_COMPLETED = "task_completed"
EVENT_AGENT_COMPLETED = "agent_completed"
EVENT_CREW_STARTED = "crew_started"
EVENT_CREW_COMPLETED = "crew_completed"
EVENT_CREW_FAILED = "crew_failed"
EVENT_DONE = "done"
EVENT_ERROR = "error"
EVENT_LOG = "log"


@dataclass
class ProgressEvent:
    """A single progress event emitted to SSE subscribers."""

    type: str
    run_id: str
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"type": self.type, "run_id": self.run_id, **self.payload}


# ---- CrewAI event listener --------------------------------------------------

_TASK_LABELS = {
    "planning_task": "Planning research",
    "research_task": "Web research",
    "fact_check_task": "Fact-checking",
    "report_task": "Writing report",
    "editing_task": "Editing report",
    "blog_writing_task": "Writing blog post",
    "seo_task": "Generating SEO metadata",
}

_AGENT_TO_TASK = {
    "research_planner": "planning_task",
    "senior_researcher": "research_task",
    "fact_checker": "fact_check_task",
    "report_writer": "report_task",
    "editor": "editing_task",
    "blog_writer": "blog_writing_task",
    "seo_specialist": "seo_task",
}


class _RunEventListener(BaseEventListener):
    """Translates CrewAI events into ProgressEvents on a per-run queue."""

    def __init__(self, run_id: str, queue: "Queue[ProgressEvent]"):
        super().__init__()
        self._run_id = run_id
        self._queue = queue
        self._seen_tasks: set[str] = set()

    def setup_listeners(self, crewai_event_bus):  # type: ignore[override]
        @crewai_event_bus.on(CrewKickoffStartedEvent)
        def _on_crew_started(source, event):
            self._queue.put(
                ProgressEvent(
                    EVENT_CREW_STARTED,
                    self._run_id,
                    {"message": "Crew started"},
                )
            )

        @crewai_event_bus.on(TaskCompletedEvent)
        def _on_task_done(source, event):
            try:
                task_obj = getattr(event, "task", None)
                task_id = getattr(task_obj, "id", None) or getattr(task_obj, "name", "task")
            except Exception:
                task_id = "task"

            label = _TASK_LABELS.get(task_id, task_id)
            self._seen_tasks.add(task_id)

            output = ""
            try:
                output_obj = getattr(task_obj, "output", None)
                if output_obj is not None:
                    output = getattr(output_obj, "raw", None) or str(output_obj)
            except Exception:
                pass

            self._queue.put(
                ProgressEvent(
                    EVENT_TASK_COMPLETED,
                    self._run_id,
                    {
                        "task_id": task_id,
                        "label": label,
                        "completed": sorted(self._seen_tasks),
                        "total": len(_TASK_LABELS),
                    },
                )
            )

            # Persist artifact as soon as it lands.
            with Session(database.get_engine()) as session:
                run = session.get(Run, self._run_id)
                if run is None:
                    return
                column_map = {
                    "planning_task": "plan",
                    "research_task": "dossier",
                    "fact_check_task": "dossier",
                    "report_task": "report",
                    "editing_task": "report",
                    "blog_writing_task": "blog",
                    "seo_task": "seo",
                }
                column = column_map.get(task_id)
                if column and output:
                    setattr(run, column, output)
                run.current_step = _TASK_LABELS.get(task_id, task_id)
                run.progress = min(100, int(len(self._seen_tasks) / len(_TASK_LABELS) * 100))
                run.updated_at = datetime.utcnow()
                session.add(run)
                session.commit()

        @crewai_event_bus.on(AgentExecutionCompletedEvent)
        def _on_agent_done(source, event):
            try:
                agent_obj = getattr(event, "agent", None)
                role = getattr(agent_obj, "role", "agent")
            except Exception:
                role = "agent"
            self._queue.put(
                ProgressEvent(
                    EVENT_AGENT_COMPLETED,
                    self._run_id,
                    {"agent_role": role},
                )
            )

        @crewai_event_bus.on(CrewKickoffCompletedEvent)
        def _on_crew_done(source, event):
            self._queue.put(
                ProgressEvent(
                    EVENT_CREW_COMPLETED,
                    self._run_id,
                    {"message": "Crew completed"},
                )
            )

        @crewai_event_bus.on(CrewKickoffFailedEvent)
        def _on_crew_failed(source, event):
            err = getattr(event, "error", None)
            self._queue.put(
                ProgressEvent(
                    EVENT_CREW_FAILED,
                    self._run_id,
                    {"error": str(err) if err else "Unknown error"},
                )
            )


# ---- Runner ----------------------------------------------------------------

class CrewRunner:
    """High-level orchestrator: kicks off the crew in a background thread and
    exposes a per-run SSE queue.

    Lifecycle:
        runner = CrewRunner(run_id, topic)
        listener = await runner.start()     # registers listener, spawns thread
        async for ev in runner.events():    # SSE consumer
            ...
        await runner.wait()
    """

    def __init__(self, run_id: str, topic: str):
        self.run_id = run_id
        self.topic = topic
        self._queue: "Queue[ProgressEvent]" = Queue()
        self._listener: Optional[_RunEventListener] = None
        self._thread: Optional[threading.Thread] = None
        self._result = None
        self._error: Optional[BaseException] = None
        self._started_at = time.monotonic()
        self._done_event = asyncio.Event()

    async def start(self) -> None:
        """Register the event listener and spawn the worker thread."""
        self._listener = _RunEventListener(
            run_id=self.run_id,
            queue=self._queue,
        )

        self._thread = threading.Thread(
            target=self._run_in_thread,
            name=f"crew-{self.run_id}",
            daemon=True,
        )
        self._thread.start()

    def _run_in_thread(self) -> None:
        try:
            settings = get_settings()
            output_dir = ensure_output_dir(self.run_id, base=settings.output_dir)

            crew_instance = ResearchAndBlogCrew()
            result = crew_instance.crew().kickoff(
                inputs={
                    "topic": self.topic,
                    "current_year": str(datetime.now().year),
                    "run_id": self.run_id,
                }
            )
            self._result = result
            self._finalize(success=True)
        except BaseException as exc:  # noqa: BLE001
            self._error = exc
            self._finalize(success=False, error=exc)
        finally:
            # Signal completion to any asyncio consumer.
            try:
                loop = asyncio.get_event_loop_policy().get_event_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                loop.call_soon_threadsafe(self._done_event.set)
            else:
                self._done_event.set()

    def _finalize(self, success: bool, error: Optional[BaseException] = None) -> None:
        duration = time.monotonic() - self._started_at

        # Try to collect final artifacts from result if available.
        report_text = None
        blog_text = None
        seo_text = None
        plan_text = None
        dossier_text = None
        token_usage = None

        if success and self._result is not None:
            try:
                tasks_output = getattr(self._result, "tasks_output", []) or []
                for t in tasks_output:
                    tid = getattr(t, "id", "") or getattr(t, "name", "")
                    raw = getattr(t, "raw", None) or str(t)
                    if tid == "planning_task":
                        plan_text = raw
                    elif tid == "research_task":
                        dossier_text = raw
                    elif tid == "fact_check_task":
                        dossier_text = raw
                    elif tid == "report_task":
                        report_text = raw
                    elif tid == "editing_task":
                        report_text = raw
                    elif tid == "blog_writing_task":
                        blog_text = raw
                    elif tid == "seo_task":
                        seo_text = raw
            except Exception:
                pass

            try:
                tu = getattr(self._result, "token_usage", None)
                if tu is not None:
                    token_usage = json.dumps(tu, default=str)
            except Exception:
                pass

        error_str = None
        if not success and error is not None:
            error_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))[-4000:]

        with Session(database.get_engine()) as session:
            run = session.get(Run, self.run_id)
            if run is not None:
                if plan_text and not run.plan:
                    run.plan = plan_text
                if dossier_text and not run.dossier:
                    run.dossier = dossier_text
                if report_text and not run.report:
                    run.report = report_text
                if blog_text and not run.blog:
                    run.blog = blog_text
                if seo_text and not run.seo:
                    run.seo = seo_text
                if token_usage:
                    run.token_usage_json = token_usage
                run.status = "completed" if success else "failed"
                run.progress = 100 if success else run.progress
                run.current_step = "Done" if success else "Failed"
                run.duration_seconds = duration
                if error_str:
                    run.error = error_str
                run.updated_at = datetime.utcnow()
                session.add(run)
                session.commit()

        self._queue.put(
            ProgressEvent(
                EVENT_DONE,
                self.run_id,
                {
                    "status": "completed" if success else "failed",
                    "duration_seconds": duration,
                    "error": error_str,
                },
            )
        )

    async def events(self):
        """Async iterator over ProgressEvents until the crew is done."""
        while True:
            try:
                ev = await asyncio.to_thread(self._queue.get, timeout=1.0)
                yield ev
                if ev.type == EVENT_DONE:
                    return
            except Empty:
                if self._done_event.is_set() and self._queue.empty():
                    return
                continue

    async def wait(self) -> None:
        await self._done_event.wait()


# ---- Module-level registry of active runners (in-memory) -------------------

_runners: dict[str, CrewRunner] = {}


def register_runner(runner: CrewRunner) -> None:
    _runners[runner.run_id] = runner


def get_runner(run_id: str) -> Optional[CrewRunner]:
    return _runners.get(run_id)


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]
