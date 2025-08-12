# FinVault Backend

FastAPI backend for FinVault with passwordless auth, risk scoring, RBAC, and hardened security middleware.

## Features

- Passwordless auth: magic link, WebAuthn, behavioral step-up
- Login/transaction risk scoring (low ≤ 40, medium 41–60, high > 60)
- Step-up policy: successful verification grants session with risk=low
- Active learning only from successful logins (no learning from medium/high or failed step-ups)
- Security: CORS, CSRF (double-submit), security headers, trusted hosts, rate limits
- Stores behavior profiles and telemetry in MongoDB (with retention for geo tiles)

## Setup

1. Create and activate venv

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Configure environment (.env in backend/)

```
ENVIRONMENT=development
POSTGRES_URI=postgresql+asyncpg://user:password@host:port/dbname
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/dbname
REDIS_URI=redis://localhost:6379/0
JWT_SECRET=replace-with-32+chars
COOKIE_SECURE=0
```

4. Run

```bash
uvicorn app.main:app --reload
```

## Production Notes

- Set `ENVIRONMENT=production` and `COOKIE_SECURE=1`.
- CORS allows `https://securebank-lcz1.onrender.com` and `https://finvault-g6r7.onrender.com`.
- CSRF cookie `csrf_token` is SameSite=None and Secure (prod); send `X-CSRF-Token` header on unsafe methods.

## API Docs

Swagger: http://localhost:8000/docs

## Structure

```
backend/
├── app/
│   ├── main.py
│   ├── security.py
│   ├── api/
│   ├── middlewares/
│   ├── models/
│   ├── schemas/
│   └── services/
└── README.md
```
