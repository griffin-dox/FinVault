# Testing

## Backend

- Recommend pytest structure under `backend/tests/`
- Add unit tests for risk_engine (device tolerance, geo fallback, ASN weighting)
- Add integration tests for telemetry endpoint and Mongo upserts (use test DB)

## Frontend

- Use Vitest + React Testing Library
- Add tests for hooks (auth, telemetry)

## Lint/Format

- Python: flake8/black
- JS/TS: eslint/prettier

## CI (future)

- GitHub Actions matrix: lint, typecheck, tests
