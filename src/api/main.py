"""FastAPI app entry point.

Run locally:
    uv run uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.config import get_settings
from api.database import init_db
from api.routes import research, runs


def _configure_logging() -> None:
    level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        stream=sys.stdout,
    )


_configure_logging()
log = logging.getLogger("api")

settings = get_settings()
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=(
        "Production API for the 6-agent Research & Blog Crew. "
        "Supports topic submission, live SSE progress streaming, and run history."
    ),
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.effective_cors_origins() + ["*"],  # dev/demo: open
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    # Ensure the output directory exists (Render mounts disk at /var/data).
    try:
        settings.output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        log.warning("Could not create output dir %s: %s", settings.output_dir, exc)
    log.info("API ready: %s v%s", settings.api_title, settings.api_version)
    log.info("Database: %s", settings.database_url)
    log.info("Output dir: %s", settings.output_dir)


@app.get("/", include_in_schema=False)
def root() -> JSONResponse:
    return JSONResponse(
        {
            "name": settings.api_title,
            "version": settings.api_version,
            "docs": "/docs",
            "api": settings.api_prefix,
        }
    )


app.include_router(research.router, prefix=settings.api_prefix)
app.include_router(runs.router, prefix=settings.api_prefix)
