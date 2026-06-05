"""Database models for run history."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Run(SQLModel, table=True):
    """A single research & blog crew execution."""

    __tablename__ = "runs"

    id: str = Field(primary_key=True, index=True)
    topic: str = Field(index=True)
    status: str = Field(default="pending", index=True)  # pending|running|completed|failed
    current_step: str = Field(default="")
    progress: int = Field(default=0)  # 0-100
    error: Optional[str] = Field(default=None)
    report: Optional[str] = Field(default=None)
    blog: Optional[str] = Field(default=None)
    seo: Optional[str] = Field(default=None)
    plan: Optional[str] = Field(default=None)
    dossier: Optional[str] = Field(default=None)
    duration_seconds: Optional[float] = Field(default=None)
    token_usage_json: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
