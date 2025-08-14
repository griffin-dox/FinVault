# FinVault – Comprehensive Progress Report

Date: 2025-08-14

This report documents the current state of the FinVault project end-to-end, for both technical and non-technical stakeholders. It serves as the main project doc and as an ongoing progress report.

## Table of contents

- Executive Summary
- KPI Dashboard
- Architecture Overview + Diagram
- Recent Changes & Achievements
- In-Progress
- Known Issues / Limitations
- Next Steps / Roadmap
- Technical Details
  - Environments and configuration
  - Data and services
  - Security model
  - Authentication and step-up flows
  - Risk engine and telemetry
  - API surface and key endpoints
  - Frontend application
  - Dependency inventory status
  - Quality gates snapshot
  - Requirement coverage mapping
- Security Posture
- Appendix
  - Detailed Change History
  - File Map (selected)
  - Glossary

## Executive Summary

FinVault is a secure, AI-powered banking MVP focused on passwordless authentication, step-up verification, and real-time risk scoring. The core flows are stabilized with robust CSRF/CORS/CSP protections, environment-aware cookies, and unified JWT handling. Step-up success now grants a full session and triggers profile learning, reducing friction over time.

Production readiness has been verified for the Render deployment (https://finvault-g6r7.onrender.com). The backend surface was cleaned up (duplicate app wiring removed, test endpoints gated in non-prod, HEAD / added). The frontend is resilient across localhost and 127.0.0.1 without base URL changes, and a utility endpoint replaced external IP dependencies. Remaining work centers on test/CI enablement, optional session guardian integration, transaction UX polish, and expanded behavioral analytics.

## KPI Dashboard

Note: Metrics collection hooks are in place conceptually; formal dashboards require CI/telemetry wiring.

- Risk engine accuracy rate: TBD (define ground truth via labeled sessions; target ≥ 95% low/medium/high correctness on labeled set).
- Average login friction time: TBD (from login start to dashboard; target P95 < 2.0s low-risk, < 5.0s after step-up).
- Step-up challenge success rate: TBD (target ≥ 75% for legitimate users; monitor false challenge rate).
- API uptime: TBD (Render + app health probes; target ≥ 99.5%).
- Bug/issue closure rate: TBD (requires issue tracking integration).
- Test coverage %: TBD (after CI; target ≥ 70% backend critical paths initially).

## Architecture Overview + Diagram

High-level components

- Frontend (React/TS, Vite, Wouter, TanStack Query).
- Backend (FastAPI, modular routers, services, security middlewares).
- Datastores (Postgres via SQLAlchemy async, Mongo via Motor, Redis asyncio).
- Auxiliary (Celery scaffolding optional, email/SMS stubs, rate limiting via SlowAPI).

Data flow (illustrative)

```mermaid
flowchart LR
  User[User Browser]
  FE[Frontend (React/TS)]
  API[FastAPI Backend]
  PG[(Postgres)]
  MG[(MongoDB)]
  RD[(Redis)]

  User -->|HTTPS| FE
  FE -->|CSRF fetch /csrf-token| API
  FE -->|Login + telemetry| API
  API -->|Risk score| API
  API --> PG
  API --> MG
  API --> RD
  FE <-->|JWT (cookie/Bearer)| API
  FE -->|Transactions/Queries| API
  API -->|Alerts| FE
```

## Recent Changes & Achievements

- Risk engine
  - Added ASN-aware IP weighting with `CARRIER_ASN_LIST` (down-weights carrier/mobile networks)
  - Implemented city-level IP geo fallback when browser geolocation is missing or low-accuracy (>500m)
  - Mirrored ASN/city fallback logic in session scoring
  - Improved device comparison tolerance (browser brand+major, OS family, screen ±100px)
- Telemetry & GeoIP
  - Local MaxMind GeoLite2 (ASN + City) enrichment with auto-detection from `data/` or `backend/data/`
  - Redis caching for IP enrichment (`GEOIP_CACHE_TTL_SEC`) to reduce mmdb reads
  - Privacy hardening: do not store IP lat/lon; store only city/region/country (+ISO)
  - IP extraction precedence from proxy headers; device/IP upsert and linking
  - Known-network tracking via per-user prefix/day counters; promotion/demotion with env thresholds
- Analytics
  - New endpoints: `GET /telemetry/known-networks/summary` and `GET /telemetry/known-networks/decay-report`
- Docs & DX
  - Added/updated docs (README, CONFIG, RISK_ENGINE, TELEMETRY, API, TESTING, OPERATIONS, CONTRIBUTING)
  - Added `backend/.env.example`
- Fixes
  - Corrected indentation causing reload error in auth flow; fixed SlowAPI limiter argument on telemetry analytics

## In-Progress

- Session guardian integration on the frontend (optional)
- CI pipeline definition and initial tests (risk engine, telemetry upserts, auth flows)
- Structured logging and error taxonomy; reduce debug prints
- Transaction UX polish and clearer challenge/block messaging
- Admin analytics UI for known-network summaries and decay report

## Known Issues / Limitations

Priority: Critical

- No CI pipeline yet — risk of regressions without automation.

Priority: Major

- Transaction flow UX needs refinement for missing/invalid IDs and challenge explanations.
- Risk engine weighting still evolving; potential drift until labeled data/monitoring is in place.

Priority: Minor

- WebAuthn availability varies by browser/platform; ensure fallbacks.
- Verbose debug logging present in some auth/risk paths.

## Next Steps / Roadmap

- Stand up CI (lint/typecheck/tests + smoke tests post-deploy)
- Health/metrics: add readiness details for Mongo/Redis and optional Prometheus metrics
- Implement structured logging (JSON) and error monitoring
- Finalize transaction flows and user-facing risk/challenge UX
- Decide on Celery vs. simple async tasks; prune scaffolding accordingly
- Expand behavioral analytics; add drift detection schedules
- Grow test suite (risk thresholds incl. ASN/city fallback, telemetry, WebAuthn)

## Technical Details

### Environments and configuration

- Deliver a secure, AI-powered banking MVP with passwordless auth, step-up verification, real-time risk scoring, and admin analytics.
- Maintain strong cross-origin security (CSRF/CORS/CSP), with frictionless UX across localhost/127.0.0.1 and production.
- Ensure successful step-up verification results in a full session and learning for reduced future friction.
- Keep a minimal, well-documented production surface and predictable deployment configuration.

Success indicators

- Low-risk logins auto-admit; medium risk triggers step-up; on success, user is admitted as low-risk.
- No CSRF/CORS/TrustedHost/CSP regressions across dev/prod.
- WebAuthn registration and authentication available and gated by Redis state.
- Clear admin visibility into alerts and risk events.

Architecture details are summarized above; see diagram. Security middlewares are applied in correct order (CORS outermost), CSRF double-submit is enforced, and TrustedHost/CSP are environment-aware.

Core environment variables (descriptive)

- POSTGRES_URI: SQLAlchemy async DSN for PostgreSQL (e.g., postgresql+asyncpg://...).
- MONGO_URI/MONGO_DB: Mongo connection and database name used by Motor.
- REDIS_URI: Redis connection string (used by FastAPI app and WebAuthn state).
- JWT_SECRET, JWT_ALGORITHM: Secret and algorithm for issuing/decoding JWT.
- ENVIRONMENT: development or production, toggles cookie flags, CSP, and test endpoints.
- COOKIE_SECURE: 1 in production to enforce Secure cookies with SameSite=None.

Cookie/CSRF policy

- Cookies: HttpOnly access_token for auth; readable csrf_token for double-submit.
- SameSite: Lax in dev, None in production; Secure flag set in production.
- CSRF endpoint: GET /csrf-token returns csrf_token cookie; requests must echo X-CSRF-Token header.

CORS/CSP/TrustedHost

- CORSMiddleware is applied outermost with allowed origins per environment.
- CSP (SecurityHeadersMiddleware): dev widened connect-src for local development; production tightened to self and API host.
- TrustedHost configured to expected domains/hosts.

Production host alignment

- Production API: https://finvault-g6r7.onrender.com
- Cookies are Secure and SameSite=None.
- CORS origins include the production frontend/API; test endpoints disabled in prod.

### Data and services

Relational models (SQLAlchemy)

- user.py, session.py, transaction.py, audit_log.py – persistent entities for core banking and auditing flows.

MongoDB collections

- Behavior/risk profiles, device fingerprints, known networks, and baseline histories (managed within auth/risk flows).

Redis

- Session states and ephemeral data, including WebAuthn challenge state and session risk flags (session guardian).

Key services

- risk_engine.py: Calculates login/session risk with reasons (device/geo/typing/mouse/IP/missing signals), thresholds, and outputs risk level.
- token_service.py: Issues/decodes JWT using a unified secret/algorithm; provides robust header/cookie parsing.
- alert_service.py: In-memory alert log and optional Celery dispatch for async notifications.
- audit_log_service.py: Persists key security and auth events to the database.
- email_service.py/sms_service.py: Stubs for outbound messaging.
- rate_limit.py / SlowAPI: Rate limiting utilities.

### Security model

- CSRF: Double-submit strategy with csrf_token cookie and X-CSRF-Token header; strict in production.
- CORS: Explicit allowlist per environment; middleware ordered before others.
- CSP: Limits sources; dev allows localhost ranges; production allows self and API only.
- Cookies: HttpOnly access_token and readable csrf_token; SameSite/Secure based on ENV.
- JWT: Unified secret and algorithm across issuers/consumers; tokens accepted either via HttpOnly cookie or Authorization Bearer header.
- RBAC: Dependency extracts JWT claims and enforces role-based access where required.
- Rate limiting: SlowAPI integrated; custom error handling.
- TrustedHost: Restricts hosts in production to mitigate host header attacks.

### Authentication and step-up flows

Primary login

- Frontend collects identifier and telemetry (including IP via /api/util/ip).
- Backend scores risk (risk_engine); returns:
  - Low risk: issues cookies and JWT; returns user + token.
  - Medium risk: returns step-up required; frontend routes to /additional-verification.
  - High risk: blocks and logs alert.

Step-up (additional verification)

- On successful challenge (context or ambient verification), backend:
  - Issues full session cookies/JWT, sets risk=low, updates learning profile (devices, networks, baselines, streaks).
  - Frontend stores session and redirects to dashboard.

WebAuthn

- Register: /webauthn/register/begin -> Redis state -> /webauthn/register/complete.
- Auth: /webauthn/auth/begin -> Redis state -> /webauthn/auth/complete -> JWT issuance.
- Redis TTLs protect challenge flow integrity.

Learning policy

- Learn only on successful low-risk login and successful step-up; never learn from medium/high-risk attempts or failed challenges.

### Risk engine and telemetry

- Inputs include device fingerprint, IP, geo, typing cadence, mouse dynamics, known networks, and prior baselines.
- Outputs a numeric score, level (low/medium/high), and reasons including missing signals.
- Maintains EWMA baselines and baseline versions; tracks low-risk streaks to stabilize profiles.
- Session guardian endpoints (optional) allow in-session telemetry updates and real-time risk checks backed by Redis/Mongo.

### API surface and key endpoints

System/meta

- GET / -> health/info page; HEAD / -> 200 for probes; GET /health; GET /csrf-token; GET /redis-check.
- Test endpoints under /test-cors are gated to non-production environments.

Auth

- POST /api/auth/login (risk-evaluated login).
- POST /api/auth/additional-verification/context-answer
- POST /api/auth/additional-verification/ambient-verify
- WebAuthn: POST /api/auth/webauthn/register/begin, /complete; /webauthn/auth/begin, /complete.
- GET /api/auth/webauthn/devices; POST /api/auth/webauthn/device/remove.

Utility

- GET /api/util/ip – returns server-observed client IP.

Transactions/Admin (representative)

- Transactions: risk-aware transaction initiation with alerts on medium/high (challenge/block).
- Admin: analytics and last 50 alerts (via alert_service) exposed through admin routes.

### Frontend application

- Structure: Vite + React TS; pages include Login, AdditionalVerification, Dashboard/Transactions; ErrorBoundary is present.
- Query client: Ensures CSRF token presence, includes credentials, and adds Authorization header when token exists.
- Resiliency: If a network error occurs, it retries swapping localhost and 127.0.0.1 for seamless dev UX.
- Auth storage: Stores user and token (securebank_token) on success; logout clears both.
- Routing: Wouter-based; medium-risk logins navigate to /additional-verification; low-risk to /dashboard.

## Security Posture

Threat model snapshot

- CSRF mitigated via double-submit and strict prod checks.
- Cross-origin risks mitigated via CORS allowlist, TrustedHost, and CSP.
- Session hijack mitigated by HttpOnly cookies and Authorization fallback; SameSite/Secure enforced by ENV.
- Replay/forgery for WebAuthn guarded by Redis-backed challenge state with TTLs.

Recent security checks

- Dependency hygiene pass (unused packages removed); pending automated SCA/DAST.
- Manual probe hardening (HEAD / added, /test-cors gated to non-prod).

Pending mitigations

- CI with dependency scanning and SAST.
- Structured logging with security event tagging and centralization.
- Strong JWT secret validation and rotation guidance.

## Recent changes and results (completed)

- Cross-origin auth stabilized: CSRF/CORS/CSP configured; SameSite and Secure cookies per ENV; Authorization fallback added.
- Step-up success leads to a full session and is treated as low risk; learning updates profile.
- IP enrichment: Dropped external ipify; added /api/util/ip and server-side header parsing.
- 401 fix: Unified JWT encode/decode; accept cookie or Bearer; resolved timing and host mismatches.
- Host alignment: Implemented transparent localhost↔127.0.0.1 fallback without forcing base URL changes.
- Backend cleanup: Consolidated main.py, removed duplicates, added HEAD /, gated /test-cors in non-prod only.
- Documentation refresh: Root and backend READMEs updated with latest security/auth/risk behavior.
- Dependency hygiene: Removed unused passlib[bcrypt] and email-validator from backend/requirements.txt.

## Testing & QA Status

Current

- Manual end-to-end testing of auth, step-up, and cross-origin flows (dev + prod endpoints).
- Ad-hoc verification of cookie flags, CSRF header matching, and CORS.

Planned

- Unit tests: token_service, risk_engine thresholds, CSRF middleware.
- Integration tests: login → step-up → dashboard, WebAuthn register/authenticate.
- Smoke tests post-deploy: /health, /csrf-token, a simple login round-trip.

Risks

- Without CI, regressions may slip through; prioritize automating critical paths first.

## Performance Benchmarks

Status: Baseline performance not yet measured. Proposed KPIs and methods:

- Login latency (low-risk path): measure time from login request to token issuance; target P95 < 2.0s.
- Step-up completion time: challenge start to dashboard; target P95 < 5.0s.
- DB timings: sample Postgres/Mongo query latencies in logs; watch for P95 outliers.
- Redis ops: track challenge state get/set timings; ensure stable under load.

## Partially complete / in progress

- Session guardian: Endpoints ready; frontend integration optional and pending.
- Celery: Scaffolding present; background workers/beat not required for MVP; decision pending.
- Transaction UX: Improve handling of invalid IDs and user-facing messaging on challenges/blocks.
- Logging: Reduce debug prints in auth/risk for production-grade logs.
- Tests/CI: Test strategy definition and CI pipeline setup pending.

## Next Steps / Roadmap

Security/ops

- Enforce strong JWT_SECRET checks across environments; consider rotation plan.
- Finalize CORS/CSRF origins list for any additional production frontend(s).
- Implement structured logging (JSON) and integrate error monitoring.

Features

- Expand behavioral analytics and fraud detection: additional signals, scheduled drift checks.
- Complete transaction flows with clear step-up/challenge UX.

Infrastructure

- Decide on Celery removal or adoption; if removed, replace with simple async tasks.
- Add CI to run lint/typecheck/tests on PRs and main.

Docs/tests

- Expand API docs and onboarding; add unit/integration tests for auth, step-up, risk thresholds, and WebAuthn flows.

## Known Issues / Risks

- Cross-site cookie constraints: Use HTTPS in production, SameSite=None + Secure; Bearer header fallback mitigates browser variations.
- Service availability: Ensure Redis/Postgres/Mongo availability; use /health and /redis-check for probes and readiness.
- JWT drift: All components now use the same secret/alg; add startup validation and fail-fast if misconfigured.
- Redis TTL/eviction: WebAuthn relies on Redis state; verify TTLs and eviction policies under load.

### Dependency inventory status

Runtime dependencies in use

- fastapi, uvicorn[standard], pydantic[email], sqlalchemy[asyncio], asyncpg, motor, pymongo, python-jose[cryptography], redis, fido2, slowapi, python-dotenv, pytz.

Removed as unused

- passlib[bcrypt], email-validator (pydantic[email] already includes email validation).

Developer tooling (dev-only)

- black, flake8 – keep out of production image if desired by moving to a dev requirements file/CI.

### Quality gates snapshot

- Build: Not executed as part of this report.
- Lint/Typecheck: Not executed as part of this report; recent static checks on edited files were clean.
- Tests: Not executed as part of this report; tests folder exists; strategy pending.

Recommendation: Add CI to enforce lint/typecheck/tests and run a smoke test after deploy.

### Requirement coverage mapping

- Step-up success grants access at low risk — Done (backend + frontend).
- IP without external dependency — Done (/api/util/ip + header enrichment).
- 401s after step-up resolved (JWT/cookie alignment) — Done (unified token processing; Authorization fallback).
- Support localhost and 127.0.0.1 without base URL changes — Done (query client fallback).
- Production readiness for Render host with CORS/CSRF/cookies — Done (verified and documented).
- Remove unused origins reference and duplicate app wiring — Done (main.py consolidated; /test-cors gated).
- Learn only from successful logins/step-ups — Done.
- Dependency cleanup — Done.
- Expand docs/tests/security hardening — Partial/Planned.

### Change log (high-level)

- Fixed duplicate Login CTAs and TS issues; corrected transaction endpoint usage.
- Implemented /csrf-token; ordered CORS correctly; widened dev CSP connect-src.
- Added /additional-verification route/page; medium risk now routes correctly without 404s.
- Replaced ipify with /api/util/ip and backend IP enrichment.
- Unified JWT decode and accepted cookies/Bearer; fixed SameSite and Authorization timing issues.
- Implemented host fallback for localhost ↔ 127.0.0.1 in the client.
- Verified production base (finvault-g6r7.onrender.com) and configured CORS/CSRF/cookies accordingly.
- Enabled active learning on successful step-up; confirmed low-risk learning policy.
- Consolidated backend main, added HEAD /, gated /test-cors in non-prod; removed stale references.
- Updated READMEs and added this report; removed unused backend dependencies.

### File Map (selected)

- backend/app/main.py — App wiring, security, health, CSRF, HEAD /, router includes.
- backend/app/security.py — CORS, CSRF, CSP, TrustedHost, SlowAPI.
- backend/app/api/auth.py — Auth, step-up, WebAuthn, learning on success.
- backend/app/api/transaction.py — Transaction flows with risk gating and alerts.
- backend/app/api/admin.py — Admin analytics and alerts view.
- backend/app/middlewares/rbac.py — JWT extraction and role enforcement.
- backend/app/services/risk_engine.py — Risk scoring and thresholds.
- backend/app/services/token_service.py — JWT issue/decode; aligned secrets/algs.
- backend/app/services/alert_service.py — Alerts (in-memory) and optional Celery dispatch.
- backend/app/database.py — Async Postgres, Mongo (Motor), Redis clients and index setup.
- frontend/client/src/lib/queryClient.ts — CSRF/Authorization handling; host fallback.
- docs/PROGRESS_REPORT.md — This comprehensive report.

---

## Appendix

### Detailed Change History

| Date       | Change                                                                             | Impact                                        | Owner     |
| ---------- | ---------------------------------------------------------------------------------- | --------------------------------------------- | --------- |
| 2025-08-13 | CSRF/CORS/CSP hardening; HEAD /; gated /test-cors; duplicate app wiring removed    | Stabilized cross-origin auth; reduced surface | Core team |
| 2025-08-13 | Step-up success grants full session + learning; unified JWT decode (cookie/Bearer) | Reduced friction; fixed post-step-up 401s     | Core team |
| 2025-08-13 | /api/util/ip introduced; removed external IP dependency                            | Improved reliability; fewer external calls    | Core team |
| 2025-08-13 | Frontend host fallback between localhost and 127.0.0.1                             | Smoother dev UX; fewer network mismatches     | Core team |
| 2025-08-13 | Docs updated (root/backend); progress reports added                                | Better onboarding and visibility              | Core team |
| 2025-08-13 | Dependency cleanup (removed passlib[bcrypt], email-validator)                      | Smaller attack surface; faster installs       | Core team |

### Glossary

- CSRF: Cross-Site Request Forgery; mitigated via double-submit tokens.
- CORS: Cross-Origin Resource Sharing; controls which origins can access APIs.
- CSP: Content Security Policy; restricts resource loading to reduce XSS risk.
- RBAC: Role-Based Access Control; enforces permissions via roles/claims.
- EWMA: Exponentially Weighted Moving Average; used for behavioral baselines.
- TTL: Time-To-Live; expiry for ephemeral keys (e.g., Redis challenges).
- JWT: JSON Web Token; used for stateless session tokens.
- WebAuthn: Web Authentication; FIDO2-based passwordless authentication.

Prepared for stakeholders and contributors. For operational details, consult README.md and backend/README.md.

- Outputs a numeric score, level (low/medium/high), and reasons including missing signals.
- Maintains EWMA baselines and baseline versions; tracks low-risk streaks to stabilize profiles.
- Session guardian endpoints (optional) allow in-session telemetry updates and real-time risk checks backed by Redis/Mongo.

## 8) API surface and key endpoints

System/meta

- GET / -> health/info page; HEAD / -> 200 for probes; GET /health; GET /csrf-token; GET /redis-check.
- Test endpoints under /test-cors are gated to non-production environments.

Auth

- POST /api/auth/login (risk-evaluated login).
- POST /api/auth/additional-verification/context-answer
- POST /api/auth/additional-verification/ambient-verify
- WebAuthn: POST /api/auth/webauthn/register/begin, /complete; /webauthn/auth/begin, /complete.
- GET /api/auth/webauthn/devices; POST /api/auth/webauthn/device/remove.

Utility

- GET /api/util/ip – returns server-observed client IP.

Transactions/Admin (representative)

- Transactions: risk-aware transaction initiation with alerts on medium/high (challenge/block).
- Admin: analytics and last 50 alerts (via alert_service) exposed through admin routes.

## 9) Frontend application

- Structure: Vite + React TS; pages include Login, AdditionalVerification, Dashboard/Transactions; ErrorBoundary is present.
- Query client: Ensures CSRF token presence, includes credentials, and adds Authorization header when token exists.
- Resiliency: If a network error occurs, it retries swapping localhost and 127.0.0.1 for seamless dev UX.
- Auth storage: Stores user and token (securebank_token) on success; logout clears both.
- Routing: Wouter-based; medium-risk logins navigate to /additional-verification; low-risk to /dashboard.

## 10) Recent changes and results (completed)

- Cross-origin auth stabilized: CSRF/CORS/CSP configured; SameSite and Secure cookies per ENV; Authorization fallback added.
- Step-up success leads to a full session and is treated as low risk; learning updates profile.
- IP enrichment: Dropped external ipify; added /api/util/ip and server-side header parsing.
- 401 fix: Unified JWT encode/decode; accept cookie or Bearer; resolved timing and host mismatches.
- Host alignment: Implemented transparent localhost↔127.0.0.1 fallback without forcing base URL changes.
- Backend cleanup: Consolidated main.py, removed duplicates, added HEAD /, gated /test-cors in non-prod only.
- Documentation refresh: Root and backend READMEs updated with latest security/auth/risk behavior.
- Dependency hygiene: Removed unused passlib[bcrypt] and email-validator from backend/requirements.txt.

## 11) Partially complete / in progress

- Session guardian: Endpoints ready; frontend integration optional and pending.
- Celery: Scaffolding present; background workers/beat not required for MVP; decision pending.
- Transaction UX: Improve handling of invalid IDs and user-facing messaging on challenges/blocks.
- Logging: Reduce debug prints in auth/risk for production-grade logs.
- Tests/CI: Test strategy definition and CI pipeline setup pending.

## 12) Backlog and next steps

Security/ops

- Enforce strong JWT_SECRET checks across environments; consider rotation plan.
- Finalize CORS/CSRF origins list for any additional production frontend(s).
- Implement structured logging (JSON) and integrate error monitoring.

Features

- Expand behavioral analytics and fraud detection: additional signals, scheduled drift checks.
- Complete transaction flows with clear step-up/challenge UX.

Infrastructure

- Decide on Celery removal or adoption; if removed, replace with simple async tasks.
- Add CI to run lint/typecheck/tests on PRs and main.

Docs/tests

- Expand API docs and onboarding; add unit/integration tests for auth, step-up, risk thresholds, and WebAuthn flows.

## 13) Risks and mitigations

- Cross-site cookie constraints: Use HTTPS in production, SameSite=None + Secure; Bearer header fallback mitigates browser variations.
- Service availability: Ensure Redis/Postgres/Mongo availability; use /health and /redis-check for probes and readiness.
- JWT drift: All components now use the same secret/alg; add startup validation and fail-fast if misconfigured.
- Redis TTL/eviction: WebAuthn relies on Redis state; verify TTLs and eviction policies under load.

## 14) Dependency inventory status

Runtime dependencies in use

- fastapi, uvicorn[standard], pydantic[email], sqlalchemy[asyncio], asyncpg, motor, pymongo, python-jose[cryptography], redis, fido2, slowapi, python-dotenv, pytz.

Removed as unused

- passlib[bcrypt], email-validator (pydantic[email] already includes email validation).

Developer tooling (dev-only)

- black, flake8 – keep out of production image if desired by moving to a dev requirements file/CI.

## 15) Quality gates snapshot

- Build: Not executed as part of this report.
- Lint/Typecheck: Not executed as part of this report; recent static checks on edited files were clean.
- Tests: Not executed as part of this report; tests folder exists; strategy pending.

Recommendation: Add CI to enforce lint/typecheck/tests and run a smoke test after deploy.

## 16) Requirement coverage mapping

- Step-up success grants access at low risk — Done (backend + frontend).
- IP without external dependency — Done (/api/util/ip + header enrichment).
- 401s after step-up resolved (JWT/cookie alignment) — Done (unified token processing; Authorization fallback).
- Support localhost and 127.0.0.1 without base URL changes — Done (query client fallback).
- Production readiness for Render host with CORS/CSRF/cookies — Done (verified and documented).
- Remove unused origins reference and duplicate app wiring — Done (main.py consolidated; /test-cors gated).
- Learn only from successful logins/step-ups — Done.
- Dependency cleanup — Done.
- Expand docs/tests/security hardening — Partial/Planned.

## 17) Change log (high-level)

- Fixed duplicate Login CTAs and TS issues; corrected transaction endpoint usage.
- Implemented /csrf-token; ordered CORS correctly; widened dev CSP connect-src.
- Added /additional-verification route/page; medium risk now routes correctly without 404s.
- Replaced ipify with /api/util/ip and backend IP enrichment.
- Unified JWT decode and accepted cookies/Bearer; fixed SameSite and Authorization timing issues.
- Implemented host fallback for localhost ↔ 127.0.0.1 in the client.
- Verified production base (finvault-g6r7.onrender.com) and configured CORS/CSRF/cookies accordingly.
- Enabled active learning on successful step-up; confirmed low-risk learning policy.
- Consolidated backend main, added HEAD /, gated /test-cors in non-prod; removed stale references.
- Updated READMEs and added this report; removed unused backend dependencies.

## 18) File map (selected)

- backend/app/main.py — App wiring, security, health, CSRF, HEAD /, router includes.
- backend/app/security.py — CORS, CSRF, CSP, TrustedHost, SlowAPI.
- backend/app/api/auth.py — Auth, step-up, WebAuthn, learning on success.
- backend/app/api/transaction.py — Transaction flows with risk gating and alerts.
- backend/app/api/admin.py — Admin analytics and alerts view.
- backend/app/middlewares/rbac.py — JWT extraction and role enforcement.
- backend/app/services/risk_engine.py — Risk scoring and thresholds.
- backend/app/services/token_service.py — JWT issue/decode; aligned secrets/algs.
- backend/app/services/alert_service.py — Alerts (in-memory) and optional Celery dispatch.
- backend/app/database.py — Async Postgres, Mongo (Motor), Redis clients and index setup.
- frontend/client/src/lib/queryClient.ts — CSRF/Authorization handling; host fallback.
- docs/PROGRESS_REPORT.md — Executive summary; this document expands it.

---

Prepared for stakeholders and contributors. For operational details, also consult README.md and backend/README.md.
