# FinVault

FinVault is a secure, AI-powered banking MVP with passwordless auth (magic link, WebAuthn, behavioral biometrics), real-time risk scoring, fraud analytics, and RBAC. The React SPA talks to a FastAPI backend via REST with CSRF-protected, cookie/Bearer-auth sessions.

## 🚀 Key Features

- **Passwordless Authentication**: Magic link, WebAuthn, and behavioral biometrics
- **Real-time Risk Scoring**: AI-powered fraud detection with location-based analytics
- **Admin Dashboard**: Comprehensive admin interface with interactive heatmaps
- **Advanced Analytics**: Location-based fraud detection and user activity visualization
- **Role-Based Access Control**: Secure RBAC middleware for admin operations
- **Behavioral Analytics**: Typing patterns, device fingerprinting, and network analysis
- **GeoIP Intelligence**: MaxMind-powered location enrichment with privacy protection

---

## Architecture

Backend (FastAPI):

- Modular routers: `auth`, `transaction`, `dashboard`, `admin`, `behavior_profile`, `geo`, `util`
- Security middleware: CORS, CSRF (double-submit), security headers, trusted hosts, rate limiting
- Datastores: PostgreSQL (SQLAlchemy async), MongoDB (Motor), Redis
- Risk engine: `app/services/risk_engine.py` for login and transaction scoring
- RBAC middleware: `app/middlewares/rbac.py`
- Heatmap analytics: Location-based fraud detection and user activity visualization

Frontend (React/Vite/TS):

- Query client with CSRF acquisition and credentials=include
- Authorization header fallback from stored token
- Host fallback (localhost ↔ 127.0.0.1) to smooth local dev
- Shared schemas in `frontend/client/shared/schema.ts`
- Interactive admin dashboard with Leaflet-powered heatmaps

---

## Key Behaviors

- Step-up policy: If the user passes additional verification (context/ambient), grant session and set risk=low.
- Learning policy: Active learning only on successful logins (low-risk direct, or successful step-up). No learning from medium/high risk or failed step-ups.
- IP enrichment: Backend extracts client IP from headers and `request.client`.
  - Local GeoIP enrichment via MaxMind mmdb (ASN + City) with Redis caching
  - Privacy: precise lat/lon from IP are not stored (only city/region/country)
  - Carrier ASN-aware IP weighting and city-level fallback in risk scoring
- Cookies: `access_token` is HttpOnly; `csrf_token` is readable cookie. SameSite=None in production; Secure in production.

---

## Quickstart

1. Clone

```bash
git clone <repo-url>
cd FinVault
```

2. Backend (env + run)

```bash
cd backend
cp .env.example .env   # fill in JWT_SECRET (>=32 chars), URIs, etc.
uvicorn app.main:app --reload
```

3. Frontend (dev)

```bash
cd frontend/client
npm install
npm run dev
```

---

## Production

- Frontend uses API base: `https://finvault-g6r7.onrender.com` in production builds.
- Backend ENV:
  - `ENVIRONMENT=production`
  - `COOKIE_SECURE=1`
  - `JWT_SECRET` (>=32 chars), `POSTGRES_URI`, `MONGODB_URI`, `REDIS_URI`
  - GeoIP: place `GeoLite2-ASN.mmdb` and `GeoLite2-City.mmdb` under `data/` or `backend/data/`
  - Risk tuning: `CARRIER_ASN_LIST`, `KNOWN_NETWORK_PROMOTION_THRESHOLD`, `KNOWN_NETWORK_DECAY_DAYS`, `GEOIP_CACHE_TTL_SEC`
- CORS allows `https://securebank-lcz1.onrender.com` and `https://finvault-g6r7.onrender.com`; credentials enabled.
- CSRF: Call `GET /csrf-token` to receive a `csrf_token` cookie and header; send `X-CSRF-Token` on unsafe methods.

---

## Developer Notes

- Business logic in `app/services/`; request validation in `app/schemas/`.
- Don’t bypass risk scoring or RBAC on protected routes.
- Never hardcode secrets; use `.env` (local) and platform env vars (prod).

Docs quick links

- Configuration: `docs/CONFIG.md`
- API surface: `docs/API.md`
- Admin Dashboard: `docs/ADMIN_DASHBOARD.md`
- Risk engine details: `docs/RISK_ENGINE.md`
- Telemetry & analytics: `docs/TELEMETRY.md`
- Security: `docs/SECURITY.md`
- Deployment: `docs/DEPLOYMENT.md`
- Operations: `docs/OPERATIONS.md`
- Testing strategy: `docs/TESTING.md`
- Contributing: `CONTRIBUTING.md`

---

## Lint & Format

- Python: black, flake8
- JS/TS: eslint, prettier

---

## Roadmap

- Tests and CI setup
- More behavioral analytics and fraud signals
- Improved logging/observability and error taxonomy

---

## Docs

See `docs/` for deployment, security, health checks, and cleanup.
