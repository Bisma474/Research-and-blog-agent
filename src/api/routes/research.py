"""Research endpoints: kick off a new run, stream progress."""

from __future__ import annotations

import json
import os
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


@router.get("/debug/env", tags=["meta"])
def debug_env() -> dict:
    """Return a masked view of the LLM-related env vars.

    Used to diagnose "Invalid API Key" style issues where the app is reading
    a different value than expected. Safe to expose: only shows first 4 + last 4
    chars plus the total length.
    """
    def mask(name: str) -> dict:
        v = os.getenv(name) or ""
        if not v:
            return {"name": name, "set": False, "length": 0}
        return {
            "name": name,
            "set": True,
            "length": len(v),
            "preview": (v[:4] + "..." + v[-4:]) if len(v) > 8 else "***",
        }

    keys: list[dict] = [mask("GROQ_API_KEY")]
    extras = os.getenv("GROQ_API_KEYS", "").strip()
    if extras:
        for i, k in enumerate([x.strip() for x in extras.split(",") if x.strip()], start=2):
            keys.append({**mask("GROQ_API_KEYS"), "index": i, "length": len(k)})

    return {
        "GROQ_API_KEY": mask("GROQ_API_KEY"),
        "GROQ_API_KEYS_extra_count": max(0, len(keys) - 1),
        "key_pool_size": len(keys),
        "OPENAI_API_KEY": mask("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": mask("ANTHROPIC_API_KEY"),
        "SERPER_API_KEY": mask("SERPER_API_KEY"),
        "MODEL": os.getenv("MODEL"),
    }


@router.get("/debug/groq-test", tags=["meta"])
async def debug_groq_test() -> dict:
    """Make a real call to Groq using the env-var API key.

    This is the definitive test: if this returns 200, the env var is correct
    and litellm can use it. If 401, something is wrong with the key or
    how litellm is reading it.
    """
    import traceback
    import httpx

    try:
        key = os.getenv("GROQ_API_KEY") or ""
        if not key:
            return {"status": "error", "detail": "GROQ_API_KEY is not set in the environment"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {key}"},
            )
        return {
            "status": r.status_code,
            "ok": r.status_code == 200,
            "key_length": len(key),
            "key_preview": (key[:4] + "..." + key[-4:]) if len(key) > 8 else "***",
            "detail": (r.text[:300] if r.status_code != 200 else "ok"),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "detail": f"request failed: {exc}",
            "traceback": traceback.format_exc()[-2000:],
        }


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
