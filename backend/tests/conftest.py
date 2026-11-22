"""
Shared test setup.

Database-backed tests (tests marked `db`) run the real API against a separate
Postgres database — `<your database>_test`, or TEST_DATABASE_URL if set. It is
created and migrated on first use and wiped before every test. The real
database is never touched. If Postgres isn't reachable, those tests are skipped.

This module must configure the environment before anything imports `app`,
because the app builds its database engine from DATABASE_URL at import time.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def _base_database_url() -> str | None:
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    env_file = BACKEND.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip()
    return None


def _test_database_url() -> str | None:
    if os.environ.get("TEST_DATABASE_URL"):
        return os.environ["TEST_DATABASE_URL"]
    base = _base_database_url()
    if not base:
        return None
    from sqlalchemy.engine import make_url
    url = make_url(base)
    return url.set(database=f"{url.database}_test").render_as_string(hide_password=False)


TEST_DATABASE_URL = _test_database_url()
if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key")
# Never call external services from tests
os.environ["HF_API_TOKEN"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""


def pytest_configure(config):
    config.addinivalue_line("markers", "db: needs the Postgres test database")


@pytest.fixture(scope="session")
def test_database():
    """Create (if needed) and migrate the test database once per run."""
    if not TEST_DATABASE_URL:
        pytest.skip("no DATABASE_URL / TEST_DATABASE_URL configured")
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    url = make_url(TEST_DATABASE_URL)
    assert url.database.endswith("_test"), f"refusing to run DB tests against {url.database!r}"
    try:
        admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
        with admin.connect() as conn:
            exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :d"), {"d": url.database}).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{url.database}"'))
        admin.dispose()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Postgres not reachable for DB tests: {e}")

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND, env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"alembic upgrade failed on test database:\n{result.stderr}")
    return TEST_DATABASE_URL


@pytest.fixture
def db_session(test_database):
    """A clean database for each test, plus a session for direct inspection."""
    from sqlalchemy import text
    from app.database import Base, SessionLocal, engine
    import app.models  # noqa: F401 — register models

    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    """FastAPI test client (background tasks such as scoring run before each response returns)."""
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)  # not used as a context manager → the job scheduler isn't started
