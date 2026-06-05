"""Run history endpoints: list, fetch detail, delete."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from api.database import get_session
from api.models import Run
from api.schemas import RunDetail, RunSummary


router = APIRouter()


@router.get("/runs", response_model=list[RunSummary], tags=["runs"])
def list_runs(
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
) -> list[RunSummary]:
    """List research runs, newest first."""
    statement = (
        select(Run)
        .order_by(Run.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = session.exec(statement).all()
    return [RunSummary.model_validate(r, from_attributes=True) for r in rows]


@router.get("/runs/{run_id}", response_model=RunDetail, tags=["runs"])
def get_run(run_id: str, session: Session = Depends(get_session)) -> RunDetail:
    """Fetch a single run with all generated artifacts."""
    run = session.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunDetail.model_validate(run, from_attributes=True)


@router.delete("/runs/{run_id}", status_code=204, tags=["runs"])
def delete_run(run_id: str, session: Session = Depends(get_session)) -> None:
    run = session.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    session.delete(run)
    session.commit()
