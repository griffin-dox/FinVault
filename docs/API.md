# API Overview

Base path: `/`

- Auth

  - POST /auth/login
  - POST /auth/register
  - POST /auth/verify
  - POST /auth/ambient-verify
  - POST /auth/context-question
  - POST /auth/context-answer
  - POST /auth/behavioral-verify
  - ... and WebAuthn endpoints

- Telemetry

  - POST /telemetry/device
  - GET /telemetry/known-networks/summary?days=30
  - GET /telemetry/known-networks/decay-report

- Utility
  - GET /health
  - GET /csrf-token

See Swagger at `/docs` for the full, current surface.
