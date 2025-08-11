# FinVault Backend

## Overview

This is the backend for the FinVault secure, AI-enhanced passwordless banking MVP. It uses FastAPI, PostgreSQL, MongoDB Atlas, and Redis.

## Features

- Passwordless authentication (magic link, behavioral biometrics)
- Transaction risk scoring and fraud detection
- Admin override and user management

## Tech Stack

- FastAPI
- PostgreSQL (SQLAlchemy ORM)
  Backend for FinVault: secure, AI-powered passwordless banking MVP. Built with FastAPI, PostgreSQL, MongoDB Atlas, Redis, and Celery.
- Redis (redis-py, Celery)
- Pydantic
  Real-time risk scoring (low ≤ 40, medium 41–60, high > 60)
  Device management (WebAuthn, device trust)
  Global JSON error handling
  RBAC middleware for role-based access

### 1. Clone the repository

````bash
```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
````

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the `backend/` directory with the following:

```
POSTGRES_URI=postgresql+asyncpg://user:password@host:port/dbname
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/dbname
JWT_SECRET=your_jwt_secret
REDIS_URL=redis://localhost:6379/0
EMAIL_SENDER=your@email.com
EMAIL_PASSWORD=yourpassword
```

### 5. Run the backend server

```bash
uvicorn app.main:app --reload
```

### 6. Run Celery worker (for async tasks)

```bash
celery -A app.services.email_service worker --loglevel=info
```

## API Documentation

Once running, visit [http://localhost:8000/docs](http://localhost:8000/docs) for Swagger UI.

---

## Directory Structure

```
backend/
├── app/
│   ├── main.py
 Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
│   ├── models/
│   ├── schemas/
├── .env
├── .gitignore
└── README.md
```
