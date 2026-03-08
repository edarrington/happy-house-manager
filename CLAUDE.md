# CLAUDE.md — Happy House Manager Development Guidelines

## Project Context

This is a private home management app for Erick and Jewel Darrington. It integrates Gmail, Google Drive, Google Calendar, and Todoist into a single dashboard.

## Azure Resource Names

| Resource | Name |
|---|---|
| Resource Group | `rg-happy-house-manager` |
| Static Web App | `swa-happy-house-manager` |
| Container App | `ca-happy-house-manager` |
| Container Apps Environment | `cae-happy-house-manager` |
| Container Registry | `crhappyhousemanager` |
| Cosmos DB Account | `cosmos-happy-house-manager` |
| Cosmos DB Database | `happy-house` |
| Cosmos DB Container | `users` |
| Key Vault | `kv-happy-house-manager` |
| Location | `eastus` |

## Environment Variable Reference

See `.env.example` for all required variables. Key ones:

- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — Google OAuth app credentials
- `JWT_SECRET_KEY` — Session JWT signing key
- `COSMOS_ENDPOINT` / `COSMOS_KEY` — Cosmos DB connection
- `KEY_VAULT_URL` — Azure Key Vault URL
- `NEXT_PUBLIC_BACKEND_URL` — Backend URL for frontend

## Architecture Decisions

### Multi-User Auth
- Each user (Erick / Jewel) signs in with their own Google account
- Google tokens (access + refresh) stored per-user in Cosmos DB under their `user_id` (Google sub)
- A session JWT is issued after OAuth, identifying the user
- Middleware extracts user identity from JWT and injects it as a FastAPI dependency

### Token Refresh
- Google tokens are refreshed automatically in `google_client.py` before building service objects
- Refreshed tokens are written back to Cosmos DB

### Todoist
- Each user links their own Todoist token via `POST /users/link-todoist`
- Token stored in user's Cosmos DB document

### Secrets
- In production, all secrets come from Azure Key Vault via managed identity
- Locally, secrets are read from `.env`

## Code Style

### Backend (Python)
- Use FastAPI dependency injection for current user and Google clients
- All router functions wrapped in `try/except` with `HTTPException`
- Pydantic models for request/response shapes
- Async functions throughout

### Frontend (TypeScript)
- Strict TypeScript — no `any` unless unavoidable
- React Query for all data fetching
- Tailwind CSS for styling
- App Router (Next.js 14)

## Key User IDs (for Cosmos DB)

Users are identified by their Google `sub` (subject) claim from the ID token. These are set at first login and stored as the document ID.

## Deployment

1. Push to `main` → triggers both GitHub Actions workflows
2. Backend: Docker image built, pushed to ACR, deployed to Container App
3. Frontend: Next.js built, deployed to Static Web App
