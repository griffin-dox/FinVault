# Copilot Instructions for FinVault

## Project Overview

FinVault is a secure, AI-powered banking MVP with passwordless authentication (magic link, behavioral biometrics), real-time risk scoring, fraud analytics, and admin override. Data flows from frontend (React) to backend (FastAPI) via REST API, with risk analysis and fraud detection at transaction time.

## Architecture & Patterns

- **Backend:**
  - FastAPI app (`backend/app/main.py`) with modular routers (`auth`, `admin`, `dashboard`, `transaction`)
  - Security middleware and environment validation on startup
  - Async DB: PostgreSQL (SQLAlchemy), MongoDB (Motor), Redis
  - Celery for async tasks (email, alerts)
  - Risk engine (`app/services/risk_engine.py`) for transaction scoring
  - RBAC middleware (`app/middlewares/rbac.py`) for role-based access
- **Frontend:**
  - React/TypeScript app (`frontend/client/src/`)
  - Custom hooks for authentication, device info, typing biometrics (`src/hooks/`)
  - Shared schemas/types (`shared/schema.ts`)
  - Tailwind CSS for styling

## Developer Workflows

- **Backend:**
  - Add routers in `app/api/`, import in `main.py`
  - Implement business logic/services in `app/services/`
  - Update data models in `app/models/`
  - Validate schemas with Pydantic in `app/schemas/`
  - Add Celery workers for async tasks in `app/services/`
  - Enforce RBAC via `app/middlewares/rbac.py`
- **Frontend:**
  - Use custom hooks for API calls in `src/hooks/`
  - Update shared types in `shared/schema.ts`

## Tech Stack

- Python, FastAPI, SQLAlchemy, Motor, Redis, Celery, Pydantic
- React, TypeScript, Drizzle ORM, Zod, Tailwind CSS
- PostgreSQL, MongoDB Atlas, Redis, SMTP (email)

## Do's and Don'ts

**Do:**

- Use modular routers for new API endpoints (`app/api/`)
- Put business logic in `app/services/`
- Use Pydantic schemas for validation (`app/schemas/`)
- Use custom hooks for API calls in frontend
- Store secrets in `.env` (never commit real secrets)
- Use Celery for async/background tasks
  **Don't:**
- Mix business logic with API routers
- Hardcode secrets or config
- Skip risk scoring for transactions
- Bypass RBAC middleware for protected routes
- Commit test data or credentials

## Integration Points

- Routers imported in `main.py`, security middleware applied globally, health checks at `/health`
- API calls via hooks, shared types in `shared/schema.ts`
- Celery worker for email/alerts
- JWT-based role extraction, enforced via dependency injection

## To-Do List

- Add/clarify test strategy and files
- Expand documentation (API, onboarding, security)
- Harden security (JWT, CORS, secrets)
- Add more behavioral analytics and fraud detection
- Improve error handling and logging
- Document custom hooks and shared schemas

---

For questions or unclear conventions, check `README.md` in project root and `backend/`.
