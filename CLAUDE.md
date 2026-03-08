# Happy House Manager - Claude Context

## What This Is

A private family web app for Erick and Jewel Arrington. Integrates Gmail, Google Drive, Google Calendar, and Todoist into a single unified interface.

## Architecture (v2 - Python Only)

**Single FastAPI app** that serves both HTML pages and JSON API endpoints.

```
FastAPI (main.py)
  ├── Jinja2 templates  ←─ full HTML pages
  ├── HTMX partials     ←─ dynamic updates (no page reload)
  ├── Tailwind CSS CDN  ←─ styling (no npm/build step)
  └── /api/* routes     ←─ JSON for programmatic access
```

**No JavaScript framework. No Next.js. No React. No TypeScript. No npm.**

## File Structure

```
happy-house-manager/
├── main.py                    # FastAPI app entry point
├── config.py                  # Pydantic settings
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── routers/
│   ├── auth.py                # Google OAuth + session
│   ├── gmail.py               # Gmail pages + HTMX partials
│   ├── drive.py               # Drive pages + HTMX partials
│   ├── calendar.py            # Calendar pages + HTMX partials
│   └── todoist.py             # Tasks pages + HTMX partials
├── services/
│   ├── cosmos_client.py       # Azure Cosmos DB
│   ├── google_client.py       # Google API service builders
│   ├── keyvault_client.py     # Azure Key Vault
│   └── todoist_client.py      # Todoist REST API v2
├── auth/
│   ├── google_oauth.py        # OAuth helpers
│   └── middleware.py          # Cookie session + auth middleware
├── templates/                 # Jinja2 HTML templates
│   ├── base.html              # Sidebar layout + HTMX + Tailwind
│   ├── login.html
│   ├── dashboard.html
│   ├── gmail/
│   ├── drive/
│   ├── calendar/
│   └── tasks/
├── static/
│   └── app.css
├── infra/
│   ├── main.bicep
│   └── parameters.json
└── .github/workflows/deploy.yml
```

## Infrastructure (Azure)

| Resource | Name |
|---|---|
| Resource Group | `rg-hhm-prod` |
| Container App | `ca-hhm-prod` |
| Container Apps Env | `cae-hhm-prod` |
| Container Registry | `acrhhmprod` |
| Key Vault | `kv-hhm-prod` |
| Cosmos DB | `cosmos-hhm-prod` |
| Log Analytics | `log-hhm-prod` |
| Managed Identity | `id-hhm-prod` |
| Location | `westus2` |

**No Static Web App** — single Container App serves everything.

## Auth Flow

1. GET `/auth/login` → show login page
2. GET `/auth/google` → redirect to Google OAuth
3. GET `/auth/callback` → exchange code → store tokens in Cosmos DB → set signed cookie
4. Cookie (`hhm_session`) contains a JWT decoded by `AuthMiddleware`
5. `request.state.user` available in all routes
6. GET `/auth/switch` → Google account picker for second user
7. GET `/auth/logout` → revoke token + clear cookie

## Multi-User (Erick + Jewel)

- Each user has their own Cosmos DB document keyed by Google `sub`
- Users stored with Google tokens, Todoist token, profile info
- Switch user via `/auth/switch` which triggers `prompt=select_account consent`
- Sidebar shows current user's name + avatar with "Switch User" button

## HTMX Pattern

- Full page: `GET /gmail` → renders `gmail/index.html` (extends `base.html`)
- Partial: `hx-get="/gmail/message/{id}"` → renders `gmail/message.html` (standalone fragment)
- Form: `hx-post="/gmail/send"` → renders `gmail/send_result.html`
- Delete: `hx-delete="/calendar/event/{id}"` + `hx-swap="outerHTML"` removes the `<li>`

## Local Development

```bash
# 1. Copy env file
cp .env.example .env
# Fill in GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, COSMOS_ENDPOINT, COSMOS_KEY

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# 3. Run
uvicorn main:app --reload --port 8000

# Or with Docker Compose
docker-compose up --build
```

## Deployment

```bash
# First-time: create resource group and deploy Bicep
az group create --name rg-hhm-prod --location westus2
az deployment group create \
  --resource-group rg-hhm-prod \
  --template-file infra/main.bicep \
  --parameters location=westus2 googleClientId=XXX googleClientSecret=XXX sessionSecretKey=XXX

# CI/CD: push to main branch triggers deploy.yml automatically
```

## Secrets (GitHub Actions)

| Secret | Description |
|---|---|
| `AZURE_CLIENT_ID` | Federated credential for OIDC login |
| `AZURE_TENANT_ID` | Azure AD tenant |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription |
| `ACR_LOGIN_SERVER` | `acrhhmprod.azurecr.io` |

## Key Dependencies

- `fastapi` + `uvicorn` — web server
- `jinja2` — HTML templates
- `python-multipart` — form data parsing
- `itsdangerous` + `starlette` — signed session cookies
- `python-jose` — JWT encoding/decoding
- `google-api-python-client` — Gmail, Drive, Calendar
- `azure-cosmos` — user store
- `azure-keyvault-secrets` + `azure-identity` — secrets management
- `httpx` — async HTTP (Todoist API)
