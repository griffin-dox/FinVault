# API Overview

Base path: `/`

## Authentication

- POST /auth/login - **Primary login** with identifier, behavioral challenge, and risk scoring
- POST /auth/register - User registration (creates account, sends verification email)
- POST /auth/verify - Email verification using magic link token
- GET /auth/verify - Email verification link handler (for emailed links)
- POST /auth/onboarding - Establish behavioral baseline after verification
- POST /auth/magic-link - Request magic link for step-up verification (medium risk)
- GET /auth/magic-link/verify - Verify magic link for step-up authentication
- POST /auth/context-question - Get security question for step-up verification
- POST /auth/context-answer - Answer security question for step-up verification
- POST /auth/ambient-verify - Ambient authentication using device/environment data
- POST /auth/behavioral-verify - Behavioral challenge verification
- POST /auth/webauthn/register/begin - WebAuthn registration initiation
- POST /auth/webauthn/register/complete - WebAuthn registration completion
- POST /auth/webauthn/auth/begin - WebAuthn authentication initiation
- POST /auth/webauthn/auth/complete - WebAuthn authentication completion

## Admin Dashboard

- GET /admin/transactions - Get all transactions with filtering
- GET /admin/users - Get user list with search and pagination
- GET /admin/users/{user_id} - Get detailed user information
- GET /admin/alerts - Get fraud alerts and system notifications
- GET /admin/system-status - Get system health and metrics
- PUT /admin/risk-rules - Update risk scoring rules
- GET /admin/heatmap-data - Get transaction risk heatmap data
- GET /admin/login-heatmap - Get login activity heatmap data
- GET /admin/user-activity-heatmap - Get user activity heatmap data

## Telemetry & Analytics

- POST /telemetry/device - Submit device telemetry data
- GET /telemetry/known-networks/summary?days=30 - Get network analytics
- GET /telemetry/known-networks/decay-report - Get network decay analysis

## Geo & Location

- GET /geo/users/{user_id}/heatmap - Get user-specific location heatmap

## Transactions

- POST /transaction/initiate - Initiate new transaction
- GET /transaction/{id} - Get transaction details
- PUT /transaction/{id}/status - Update transaction status

## Utility

- GET /health - Health check endpoint
- GET /csrf-token - Get CSRF token for form submissions

## Dashboard

- GET /dashboard/overview - Get user dashboard data
- GET /dashboard/transactions - Get user's transaction history

See Swagger at `/docs` for the full, current surface.
