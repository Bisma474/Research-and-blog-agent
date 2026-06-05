"""API smoke tests using FastAPI's TestClient with a temp SQLite database.

These tests cover the HTTP contract (validation, CRUD, error responses) without
actually executing a crew run, which would require live LLM credentials.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine as _sa_create_engine


@pytest.fixture(scope="module")
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    out_dir = tempfile.mkdtemp()

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["OUTPUT_DIR"] = out_dir

    from api.config import get_settings
    get_settings.cache_clear()
    from api import database as dbmod
    from api.services import crew_runner as cr
    dbmod._engine = None  # type: ignore[attr-defined]
    cr.database._engine = None  # type: ignore[attr-defined]

    temp_engine = _sa_create_engine(
        os.environ["DATABASE_URL"],
        connect_args={"check_same_thread": False},
    )
    dbmod.set_engine(temp_engine)
    cr.database.set_engine(temp_engine)

    dbmod.init_db()

    from api.main import app

    with TestClient(app) as c:
        yield c

    # Best-effort cleanup. On Windows, sqlite sometimes holds the file open
    # briefly after the test client closes; we ignore failures here.
    try:
        Path(db_path).unlink(missing_ok=True)
    except (PermissionError, OSError):
        pass


def test_health(client: TestClient):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert body["database"] == "ok"


def test_runs_initially_empty(client: TestClient):
    r = client.get("/api/v1/runs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_research_validation_rejects_short_topic(client: TestClient):
    r = client.post("/api/v1/research", json={"topic": "a"})
    assert r.status_code == 422


def test_research_validation_rejects_missing_topic(client: TestClient):
    r = client.post("/api/v1/research", json={})
    assert r.status_code == 422


def test_run_detail_returns_404_for_missing(client: TestClient):
    r = client.get("/api/v1/runs/does-not-exist")
    assert r.status_code == 404


def test_delete_run_returns_404_for_missing(client: TestClient):
    r = client.delete("/api/v1/runs/does-not-exist")
    assert r.status_code == 404


def test_openapi_schema_is_exposed(client: TestClient):
    r = client.get("/api/v1/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert "paths" in schema
    assert "/api/v1/research" in schema["paths"]
    assert "/api/v1/runs" in schema["paths"]
    assert "/api/v1/health" in schema["paths"]
