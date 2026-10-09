# Multi-Tenant Project & Workflow Management Platform

Production-oriented full-stack application with:

- **FastAPI** + **SQLAlchemy** + **PostgreSQL** + **Alembic**
- **JWT authentication** + **GitHub OAuth** (realtime)
- Multi-tenant isolation (organizations)
- Role-based + resource-based authorization
- Projects, Tasks (models ready), Comments, Notifications, Audit logs
- **Redis** + **Celery** for background jobs
- React frontend (Vite + Zustand)
- Docker Compose

Your original 30% (auth, orgs, members, projects, permissions) has been extended with GitHub OAuth, additional models, Celery, Docker, and a working React frontend.

---

## Prerequisites

- Docker & Docker Compose **(recommended)**
- OR locally: Python 3.12+, Node 20+, PostgreSQL 16, Redis 7

---

## 1. GitHub OAuth Setup (For Client ID & Secret)

1. Go to https://github.com/settings/developers → OAuth Apps
2. Authorization callback URL **must** be:
   ```
   http://localhost:8000/api/v1/auth/github/callback
   ```
3. Copy Client ID and Client Secret.

---

## 2. Environment

```bash
cd backend
cp .env.example .env
```

Edit `.env`:

```env
JWT_SECRET_KEY=some-long-random-string-at-least-32-chars
GITHUB_CLIENT_ID=your_real_client_id
GITHUB_CLIENT_SECRET=your_real_client_secret
GITHUB_REDIRECT_URI=http://localhost:8000/api/v1/auth/github/callback
FRONTEND_URL=http://localhost:5173
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/multi_tenant
```

---

## 3. Run with Docker Compose (easiest)

From the project root:

```bash
docker compose up --build
```

Services:

| Service        | URL / Port          |
|----------------|---------------------|
| Backend API    | http://localhost:8000 |
| API docs       | http://localhost:8000/docs |
| Frontend       | http://localhost:5173 |
| PostgreSQL     | localhost:5432      |
| Redis          | localhost:6379      |
| Celery worker  | (background)        |

First time – run migrations inside the backend container:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed_roles.py
```

---

## 4. Run locally (without Docker)

### 4.1 Database & Redis

```bash
# Start Postgres & Redis however you prefer
# Example with Docker only for infra:
docker run -d --name mt-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=multi_tenant -p 5432:5432 postgres:16-alpine
docker run -d --name mt-redis -p 6379:6379 redis:7-alpine
```

### 4.2 Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Create .env (see above)
alembic upgrade head
python scripts/seed_roles.py

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4.3 Celery worker (another terminal)

```bash
cd backend
source .venv/bin/activate
celery -A app.celery_app.celery worker --loglevel=info
```

### 4.4 Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## 5. Authentication flows

### Email / Password
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET  /api/v1/auth/me`

### GitHub OAuth (realtime)
1. Frontend button → `GET /api/v1/auth/github/login`
2. User authorizes on GitHub
3. GitHub redirects to `GET /api/v1/auth/github/callback`
4. Backend creates/links user + issues JWT
5. Redirects to `http://localhost:5173/auth/callback?access_token=...&refresh_token=...`
6. Frontend stores tokens and calls `/auth/me`

---

## 6. Project structure (clean architecture)

```
backend/
  app/
    api/v1/          # Routes only
    core/            # config, security, permissions
    db/              # session, base
    models/          # SQLAlchemy models
    schemas/         # Pydantic
    services/        # Business logic
    tasks/           # Celery tasks
  alembic/
  scripts/
frontend/
  src/
    pages/
    api.js
    store.js (Zustand)
```

---

## 7. What is already implemented vs next steps

**Done / Extended**
- JWT + refresh token rotation
- GitHub OAuth end-to-end
- Organizations, members, roles, permissions
- Projects CRUD (from your original code)
- Models for Task, TaskDependency, Comment, Attachment, Notification, AuditLog, ProjectMember
- Celery + Redis scaffolding
- Docker Compose full stack
- React login / register / GitHub button / dashboard / projects list
- Multi-tenant isolation patterns in deps

**Recommended next implementation order**
1. Alembic migration for the new tables (Task, etc.)
2. Task service + routes with status workflow validation & circular dependency check
3. Comment + file upload endpoints
4. Notification creation on assign/status change
5. WebSocket notification channel
6. Full Kanban board with drag-and-drop (frontend)
7. Automated pytest suite (auth, multi-tenant isolation, workflow)
8. Rate limiting, caching, CSV export, etc.

---

## 8. Security notes

- Never trust client-supplied file extensions – validate MIME + magic bytes
- Always check organization membership **and** project membership on every resource access
- Inactive users cannot authenticate or be assigned tasks
- Viewers cannot be assigned tasks
- Audit log is append-only

---

## 9. Useful commands

```bash
# New migration
alembic revision --autogenerate -m "add_tasks_and_related"

# Apply
alembic upgrade head

# Seed roles
python scripts/seed_roles.py

# API docs
open http://localhost:8000/docs
```

---

## License

Private until the assignment is complete.
