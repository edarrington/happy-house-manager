# Happy House Manager

A private family web app for Erick and Jewel Arrington. Single Python FastAPI application that integrates Gmail, Google Drive, Google Calendar, and Todoist into one unified interface.

**No JavaScript framework. No Next.js. No React. No npm.**
Jinja2 templates + HTMX + Tailwind CSS via CDN.

## Quick Start (Local)

```bash
# 1. Clone and set up environment
git clone https://github.com/edarrington/happy-house-manager.git
cd happy-house-manager

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env with your Google OAuth credentials and Cosmos DB connection

# 4. Run
uvicorn main:app --reload --port 8000
# Open http://localhost:8000
```

## Docker

```bash
docker-compose up --build
# Open http://localhost:8000
```

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create an OAuth 2.0 Client ID (Web application)
3. Add authorized redirect URI: `http://localhost:8000/auth/callback`
4. Enable APIs: Gmail, Drive, Calendar
5. Copy Client ID and Secret to `.env`

## Azure Deployment

```bash
# Create resource group
az group create --name rg-hhm-prod --location westus2

# Deploy infrastructure
az deployment group create \
  --resource-group rg-hhm-prod \
  --template-file infra/main.bicep \
  --parameters location=westus2 \
               googleClientId=YOUR_CLIENT_ID \
               googleClientSecret=YOUR_CLIENT_SECRET \
               sessionSecretKey=$(python -c "import secrets; print(secrets.token_hex(32))")

# CI/CD via GitHub Actions (push to main)
# Set secrets: AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID, ACR_LOGIN_SERVER
```

## Architecture

```
Browser
  │
  └── FastAPI (Python)
        ├── Jinja2 templates  (full page renders)
        ├── HTMX partials     (dynamic updates)
        ├── Google APIs       (Gmail / Drive / Calendar)
        ├── Todoist API
        ├── Cosmos DB         (user tokens)
        └── Key Vault         (secrets)

Deployment: single Docker container → Azure Container App
```

## Routes

| Path | Description |
|---|---|
| `GET /` | Redirect to dashboard or login |
| `GET /dashboard` | Home page with integration cards |
| `GET /gmail` | Gmail inbox |
| `GET /drive` | Drive file browser |
| `GET /calendar` | Upcoming events |
| `GET /tasks` | Todoist projects + tasks |
| `GET /auth/login` | Login page |
| `GET /auth/google` | Start Google OAuth |
| `GET /auth/callback` | OAuth callback |
| `GET /auth/switch` | Switch to other user |
| `GET /auth/logout` | Sign out |
| `GET /health` | Health check |
| `GET /api/docs` | API documentation |
