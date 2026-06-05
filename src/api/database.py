"""SQLModel database engine + session management.

The engine is built lazily on first access so that tests can override
`DATABASE_URL` (and `OUTPUT_DIR`) via the env before the engine is
constructed.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.engine import Engine

from api.config import get_settings


_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """Return the process-wide engine, creating it on first call."""
    global _engine
    if _engine is None:
        s = get_settings()

        # Ensure the SQLite parent directory exists. Render mounts the disk at
        # /var/data and we want to write runs.db there.
        if s.database_url.startswith("sqlite:///"):
            db_path = s.database_url.replace("sqlite:///", "", 1)
            # On Windows the path is just a regular path; on Render it's
            # /var/data/runs.db. Strip optional Windows drive prefix.
            if not db_path.startswith("/"):
                # e.g. "C:/var/data/runs.db" -> keep as-is on Windows
                pass
            parent = Path(db_path).parent
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                # If the directory cannot be created (read-only fs), fall back
                # to in-memory SQLite so the service still boots.
                s = s.model_copy(update={"database_url": "sqlite:///:memory:"})

        _engine = create_engine(
            s.database_url,
            echo=False,
            connect_args={"check_same_thread": False} if s.database_url.startswith("sqlite") else {},
        )
    return _engine


def set_engine(engine: Engine) -> None:
    """Override the engine (used by tests)."""
    global _engine
    _engine = engine


def init_db() -> None:
    """Create all tables. Safe to call on every startup."""
    from api import models  # noqa: F401

    SQLModel.metadata.create_all(get_engine())


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager that commits on success and rolls back on error."""
    session = Session(get_engine())
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a session."""
    session = Session(get_engine())
    try:
        yield session
    finally:
        session.close()
