# AI Risk Guard

Automated security analysis for GitHub Pull Requests. AI Risk Guard scans PRs for
common Python vulnerabilities, generates fix patches, validates them in a hardened
Docker sandbox, scores the risk, and posts a summary comment with SARIF results to
GitHub Code Scanning.

## Features

- **10 vulnerability types** — Command Injection, Code Injection, SQL Injection,
  Path Traversal, SSRF, Hardcoded Secrets, Insecure Deserialization, Weak
  Cryptography, TLS Verification Disabled, and Debug Code. The last two — TLS
  verification and leftover debug code — are the most recent additions.
- **Multi-agent pipeline** — scanner, patch, validator, risk, and orchestrator
  agents cooperate to detect, patch, validate, and score every finding
- **Patch generation** — deterministic AST fixers plus Gemini LLM innovation
- **Hardened sandbox** — Docker isolation with memory/CPU/network limits and a
  local fallback when Docker is unavailable
- **GitHub integration** — PR comments, risk labels, code review decisions,
  SARIF upload to Code Scanning, and automated feedback via reactions/merges
- **Dashboard** — React SPA with real metrics (risk scores, remediation rate,
  cache hit rate) served by Flask

## Architecture

```
GitHub PR ──► Diff-aware AST Scanner ──► Vulnerability Detection
       ──► Patch Generator (AST + Gemini) ──► Docker Sandbox Validation
       ──► Patch Quality Scoring ──► Risk Engine ──► Confidence Scoring
       ──► SARIF + PR Report + Dashboard
```

## Quick Start (local development)

### Prerequisites

- Python 3.13+
- Node.js 20+ (for the frontend)
- Docker (optional — enables sandbox isolation; falls back to local otherwise)

### 1. Configure the app

```bash
cp .env.example .env
# Fill in GITHUB_APP_ID, GITHUB_WEBHOOK_SECRET, GITHUB_APP_CLIENT_ID,
# GITHUB_APP_CLIENT_SECRET, GITHUB_PRIVATE_KEY, GEMINI_API_KEY
```

### 2. Install and run the backend

```bash
python -m pip install -r requirements.txt
python app/app.py            # serves at http://localhost:8000
```

### 3. Build and run the frontend (dev mode)

```bash
cd frontend
npm install
npm run dev                  # Vite dev server at http://localhost:3000
```

For production, build once and let Flask serve the SPA:

```bash
cd frontend && npm run build # outputs to ../static/frontend
python app/app.py            # Flask serves both API and SPA on :8000
```

## GitHub App setup

1. Create a GitHub App at <https://github.com/settings/apps>.
2. Set the **Webhook URL** to `https://<your-host>/webhook` and note the secret.
3. Grant **Pull requests** read/write, **Contents** read/write, **Checks** read/write,
   **Workflows** read/write, **Security events** read/write, and **Metadata** read
   permissions.
4. Subscribe to the **pull_request**, **installation**, and **installation_repositories**
   webhook events.
5. Set the **OAuth** client ID/secret on the app (or a separate OAuth app) for
   dashboard login.
6. Generate a private key and place it (or its contents) in `GITHUB_PRIVATE_KEY`.
7. Install the app on the repos you want scanned.

### CodeQL provisioning

When the app is installed on (or added to) a repository, it automatically opens a
pull request that adds the standard GitHub CodeQL workflow — analysis then runs on
GitHub's own hosted runners, free on public repositories. Merging the PR activates
it. Private repositories need a GitHub Code Security entitlement to view Code
Scanning alerts. Disable via the `codeql` section in `config/app.yaml`
(`enabled` / `auto_provision`).

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GITHUB_APP_ID` | Required | GitHub App JWT authentication |
| `GITHUB_PRIVATE_KEY` | Required | JWT signing (PEM content or file path) |
| `GITHUB_WEBHOOK_SECRET` | Required | Webhook signature verification |
| `GITHUB_APP_CLIENT_ID` | Required | GitHub OAuth login |
| `GITHUB_APP_CLIENT_SECRET` | Required | OAuth token exchange |
| `GEMINI_API_KEY` | Optional | LLM patch generation (falls back to AST-only) |
| `FLASK_SECRET_KEY` | Optional | Session signing (random if unset → sessions reset) |
| `GITHUB_APP_SLUG` | — | Install-app banner link |
| `SESSION_COOKIE_SECURE` | — | `true` when serving over HTTPS |
| `FRONTEND_ORIGIN` | — | CORS origin when frontend is served separately |
| `PORT` | — | Bind port override (used by Render/Heroku) |
| `DB_PATH` | — | SQLite database path (default `data/dashboard.db`) |

## Development

```bash
python -m pytest tests/ -x -q   # run tests
ruff check .                    # lint
mypy .                          # type check
cd frontend && npm run build    # frontend build
```

## Deployment

See `Deploy_Plan.md` for platform-by-platform guidance (Render, Oracle Cloud) and
`Documentation/` for architecture and status details.

## License

[MIT](LICENSE)
