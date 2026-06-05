"""Pydantic request / response schemas for the API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=200, description="The research topic.")


class RunSummary(BaseModel):
    id: str
    topic: str
    status: str
    current_step: str
    progress: int
    duration_seconds: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class RunDetail(RunSummary):
    plan: Optional[str] = None
    dossier: Optional[str] = None
    report: Optional[str] = None
    blog: Optional[str] = None
    seo: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
