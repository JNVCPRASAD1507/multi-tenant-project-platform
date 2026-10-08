from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

# backend/ must be importable when pytest is launched from backend/ or project root.
TESTS_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(TESTS_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402,F401
    AuditLog,
    Comment,
    Notification,
    Organization,
    OrganizationMember,
    Project,
    ProjectMember,
    RefreshToken,
    Role,
    Task,
    TaskDependency,
    User,
)
from app.models.attachment import Attachment  # noqa: E402,F401
from app.models.chat import ChatMessage, ChatParticipant, ChatRoom  # noqa: E402,F401
from app.models.oauth_account import OAuthAccount  # noqa: E402,F401


def _test_database_url() -> str:
    """Build an isolated test DB URL from TEST_DATABASE_URL or DATABASE_URL."""
    explicit = os.getenv("TEST_DATABASE_URL")
    if explicit:
        return explicit

    url = make_url(settings.DATABASE_URL)
    db_name = url.database or "multi_tenant"
    if not db_name.endswith("_test"):
        db_name = f"{db_name}_test"
    return url.set(database=db_name).render_as_string(hide_password=False)


def _create_database_if_needed(database_url: str) -> None:
    """Create the isolated PostgreSQL database when it does not exist."""
    url = make_url(database_url)
    database = url.database
    if not database:
        raise RuntimeError("TEST_DATABASE_URL must contain a database name.")

    # Connect to the maintenance DB using the same credentials/host.
    maintenance_url = url.set(drivername="postgresql", database="postgres")
    import psycopg

    conninfo = maintenance_url.render_as_string(hide_password=False)
    with psycopg.connect(conninfo, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (database,)
        ).fetchone()
        if not exists:
            # Database names cannot be bound as parameters; quote safely.
            safe_name = '"' + database.replace('"', '""') + '"'
            conn.execute(f"CREATE DATABASE {safe_name}")


@pytest.fixture(scope="session")
def test_engine():
    database_url = _test_database_url()
    _create_database_if_needed(database_url)
    engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)

    # Seed the roles expected by registration and RBAC.
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SessionLocal() as db:
        roles = {
            "Super Admin": "Full platform access",
            "Organization Admin": "Organization administrator",
            "Project Manager": "Project manager",
            "Team Member": "Team member",
            "Viewer": "Read-only member",
        }
        for name, description in roles.items():
            if db.query(Role).filter(Role.name == name).first() is None:
                db.add(Role(name=name, description=description))
        db.commit()

    yield engine
    engine.dispose()


@pytest.fixture()
def db(test_engine):
    """Clean the test database before every test."""
    table_names = [
        "chat_messages",
        "chat_participants",
        "chat_rooms",
        "comments",
        "notifications",
        "audit_logs",
        "attachments",
        "task_dependencies",
        "tasks",
        "project_members",
        "projects",
        "organization_members",
        "refresh_tokens",
        "oauth_accounts",
        "organizations",
        "users",
    ]

    with test_engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE TABLE " + ", ".join(table_names) +
            " RESTART IDENTITY CASCADE"
        ))

    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    with SessionLocal() as session:
        yield session


def _override_get_db(db: Session):
    def dependency():
        yield db
    return dependency


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = _override_get_db(db)
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def registered_user(client):
    payload = {
        "email": "owner@example.com",
        "password": "StrongPass123!",
        "full_name": "Tenant Owner",
        "organization_name": "Tenant One",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return payload, response.json()


@pytest.fixture()
def auth_token(client, registered_user):
    payload, data = registered_user
    response = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert response.status_code == 200, response.text
    return response.json()["tokens"]["access_token"]


@pytest.fixture()
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


def register_and_login(client, *, email: str, full_name: str, organization_name: str):
    payload = {
        "email": email,
        "password": "StrongPass123!",
        "full_name": full_name,
        "organization_name": organization_name,
    }
    register = client.post("/api/v1/auth/register", json=payload)
    assert register.status_code == 201, register.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": payload["password"]},
    )
    assert login.status_code == 200, login.text
    return payload, register.json(), login.json()


@pytest.fixture()
def second_user(client):
    return register_and_login(
        client,
        email="member@example.com",
        full_name="Tenant Member",
        organization_name="Tenant Two",
    )
