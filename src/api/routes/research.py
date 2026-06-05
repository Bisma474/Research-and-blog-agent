"""Research endpoints: kick off a new run, stream progress."""

from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse
from sqlmodel import Session, select

from api.database import get_session
from api.models import Run
from api.schemas import HealthResponse, ResearchRequest
from api.services.crew_runner import (
    CrewRunner,
    get_runner,
    new_run_id,
    register_runner,
)


router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["meta"])
def health(session: Session = Depends(get_session)) -> HealthResponse:
    """Liveness + DB check."""
    db_ok = "ok"
    try:
        session.exec(select(Run).limit(1)).first()
    except Exception as exc:  # noqa: BLE001
        db_ok = f"error: {exc}"
    settings = __import__("api.config", fromlist=["get_settings"]).get_settings()
    return HealthResponse(
        status="ok",
        version=settings.api_version,
        database=db_ok,
    )


@router.post("/research", status_code=status.HTTP_202_ACCEPTED, tags=["research"])
def start_research(
    payload: ResearchRequest,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
) -> dict:
    """Kick off a new research & blog run. Returns the run id for streaming."""
    run_id = new_run_id()
    run = Run(
        id=run_id,
        topic=payload.topic,
        status="pending",
        current_step="Queued",
        progress=0,
    )
    session.add(run)
    session.commit()

    runner = CrewRunner(run_id=run_id, topic=payload.topic)
    register_runner(runner)

    async def _bootstrap() -> None:
        await runner.start()

    background.add_task(_bootstrap)

    return {"run_id": run_id, "status": "pending"}


@router.get("/research/{run_id}/stream", tags=["research"])
async def stream_research(run_id: str, session: Session = Depends(get_session)) -> EventSourceResponse:
    """SSE stream of progress events for a run.

    If the run is still in flight, streams live events. If it has already
    finished, replays a single 'done' event so the client can render the
    final result deterministically.
    """
    runner = get_runner(run_id)

    if runner is not None:
        async def _event_gen() -> AsyncIterator[dict]:
            async for ev in runner.events():
                yield {"event": "message", "data": json.dumps(ev.to_dict())}

        return EventSourceResponse(_event_gen())

    run = session.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    async def _replay() -> AsyncIterator[dict]:
        yield {
            "event": "message",
            "data": json.dumps(
                {
                    "type": "done",
                    "run_id": run_id,
                    "status": run.status,
                    "duration_seconds": run.duration_seconds,
                    "error": run.error,
                }
            ),
        }

    return EventSourceResponse(_replay())
