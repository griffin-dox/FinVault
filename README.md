# FinVault

FinVault is a secure, AI-powered banking MVP featuring passwordless authentication (magic link, behavioral biometrics), real-time risk scoring, fraud analytics, and admin override. Data flows from frontend (React) to backend (FastAPI) via REST API, with risk analysis and fraud detection at transaction time.

---

## Architecture

**Backend:**

- FastAPI app (`backend/app/main.py`) with modular routers (`auth`, `admin`, `dashboard`, `transaction`)
- Security middleware and environment validation on startup
- Async DB: PostgreSQL (SQLAlchemy), MongoDB (Motor), Redis
- Celery for async tasks (email, alerts)
- Risk engine (`app/services/risk_engine.py`) for transaction scoring
- RBAC middleware (`app/middlewares/rbac.py`) for role-based access

**Frontend:**

- React/TypeScript app (`frontend/client/src/`)
- Custom hooks for authentication, device info, typing biometrics (`src/hooks/`)
- Shared schemas/types (`shared/schema.ts`)
- Tailwind CSS for styling

---

## Quickstart

### 1. Clone the repo

```bash
git clone <repo-url>
cd FinVault
```

### 2. Setup Backend

cp .env.example .env # Edit with your secrets
uvicorn app.main:app --reload

````bash
cd frontend/client
```bash
npm run dev:frontend
npm run dev:all
````

## Environment Variables

- See `.env.example` in both `backend/` and `frontend/client/` for required variables.

---

- Data models: update in `app/models/`

- Shared types: update in `shared/schema.ts`

- PostgreSQL, MongoDB Atlas, Redis, SMTP (email)

---

- Put business logic in `app/services/`
- Use Pydantic schemas for validation (`app/schemas/`)
- Use Celery for async/background tasks

**Don't:**

- Mix business logic with API routers
- Hardcode secrets or config
- Skip risk scoring for transactions
- Bypass RBAC middleware for protected routes
- Commit test data or credentials

---

## To-Do List

- Add/clarify test strategy and files
- Expand documentation (API, onboarding, security)
- Harden security (JWT, CORS, secrets)
- Add more behavioral analytics and fraud detection
- Improve error handling and logging
- Document custom hooks and shared schemas

---

## Linting & Formatting

- Python: `black`, `flake8`
- JS/TS: `eslint`, `prettier`
- Pre-commit hooks auto-format and lint code before commit.

---

## Contributing

- See `CONTRIBUTING.md` (coming soon)
- PRs welcome!
