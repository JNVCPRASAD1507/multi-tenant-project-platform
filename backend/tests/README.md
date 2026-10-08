# Multi-Tenant Project Platform — Backend Pytest Suite

This folder is a backend-focused pytest suite for the uploaded FastAPI multi-tenant project.

## What it covers

- Registration, login, `/auth/me`
- Invalid authentication and refresh-token rotation/revocation
- Organization membership and tenant isolation
- RBAC permission matrix
- Project CRUD and cross-organization isolation
- Task CRUD, status workflow, and dependency rules
- Cross-organization chat (intentional project design)
- Chat participant access control
- Notification/comment/audit/chat table presence
- WebSocket connection-manager behavior

## Important project status

The uploaded project contains **models + database migrations** for:

- `comments`
- `notifications`
- `audit_logs`

but it does **not** currently expose REST endpoints/services for comments or audit-log management. Notifications have a Celery creation task and a WebSocket notification channel, but no notification REST API.

The tests therefore do not pretend that those missing APIs exist.

## Run from `backend/`

Install test dependency if needed:

```powershell
pip install pytest
```

The backend requirements already contain the PostgreSQL driver (`psycopg`).

Set `TEST_DATABASE_URL` if you want a specific isolated database:

```powershell
$env:TEST_DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/multi_tenant_test"
```

If it is omitted, the suite derives `<DATABASE_NAME>_test` from the backend `DATABASE_URL` and attempts to create that database using the same PostgreSQL credentials.

Run:

```powershell
pytest tests -q
```

For more detail:

```powershell
pytest tests -v
```

For a coverage report, install `pytest-cov` and run:

```powershell
pytest tests --cov=app --cov-report=term-missing
```

## Docker setup

If PostgreSQL is running through this project's Docker Compose stack, the safest way is to run the suite inside the backend container after installing pytest there:

```powershell
docker compose exec backend pip install pytest

docker compose exec backend pytest tests -q
```

For a persistent test dependency, add pytest/pytest-cov to the project's backend development requirements rather than production requirements.

## Test philosophy

The suite intentionally uses an isolated PostgreSQL test database. It does not use the project's development database and does not delete development data.
