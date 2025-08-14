# Contributing

Thanks for your interest in improving FinVault!

## Getting Started

- Fork the repo and create a feature branch.
- Keep routers thin; place business logic in `app/services/`.
- Validate requests with Pydantic schemas; follow existing patterns.

## Code Style

- Python: black + flake8; type hints where practical
- JS/TS: eslint + prettier
- Keep changes small and focused; update docs/tests alongside code.

## Commit Messages

- Use clear, imperative style. Reference related issues when applicable.

## Pull Requests

- Include tests for new behavior
- Update docs for user-facing or config changes
- Note any breaking changes and migration steps
