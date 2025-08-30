# API Overview

Base path: `/`

## Authentication

- POST /auth/login
- POST /auth/register
- POST /auth/verify
- POST /auth/ambient-verify
- POST /auth/context-question
- POST /auth/context-answer
- POST /auth/behavioral-verify
- ... and WebAuthn endpoints

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
