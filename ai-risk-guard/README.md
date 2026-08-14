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
- **Hardened sandbox** — Docker isolation with memory/CPU/network limits;
  scans fail closed when Docker is unavailable (no host execution). Transient
  Docker restarts are retried with backoff, and scans that fail closed are
  queued for automatic re-validation once Docker returns (deferred re-validation)
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
- Docker (required for sandbox validation — scans fail closed when unavailable)

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

### Docker availability

Sandbox validation runs only inside Docker and never on the host. When Docker or
the sandbox image is unavailable, the app handles it in three layers:

1. **Retry with backoff** — transient daemon restarts are retried before failing
   closed. Configure with `retry_attempts` / `retry_backoff_seconds` in
   `config/sandbox.yaml`.
2. **Static-only validation** — the static stages (syntax, security re-scan,
   policy) still complete; findings are labelled "static-only" and the check run
   stays `neutral`, so PRs are never falsely blocked.
3. **Deferred re-validation** — scans that failed closed are marked pending, and
   a background worker re-runs them once Docker returns, updating the existing PR
   comment and check. Enable/tune via the `validation` section in
   `config/app.yaml`, or trigger manually with the **Re-validate** button on the
   Scans page.
4. **CI-runner validation** — when the App's Docker stays unavailable, the
   sandbox execution and regression tests for each failed candidate are
   dispatched to a GitHub-hosted Actions runner (via `repository_dispatch`),
   and the completed runtime evidence is re-injected into a re-analysis pass so
   the PR comment/check still show real runtime results.

### CI-runner validation (Phase E)

When local Docker is unavailable, the App cannot run the sandbox — but a
GitHub-hosted runner can. Setup:

1. **Host the workflow** in a repo that contains this codebase (the workflow
   repo). Push `.github/workflows/ai-risk-guard-validate.yml` and `ci/validate.py`
   to that repo. The default (empty `workflow_repo` → `GITHUB_REPOSITORY`) assumes
   the App's own repo, which also needs the App installed so installation-token
   dispatch works.
2. **Add a repository secret** `AI_RISK_GUARD_CI_SECRET` on the workflow repo with
   the same value as the App's `CI_VALIDATION_SECRET`.
3. **Configure the App** via the `ci_runner` section in `config/app.yaml` plus env:
   - `CI_VALIDATION_SECRET` — shared secret (must match the repo secret).
   - `CI_VALIDATION_BASE_URL` (or `ci_runner.base_url`) — public base URL of the
     App so the runner can fetch jobs and post results.
   - `CI_VALIDATION_TOKEN` (optional) — token with `repo` scope on the workflow
     repo; when unset, the App falls back to the PR repo's installation token.

Lifecycle: a candidate that failed closed is captured idempotently in the
`pending_validations` table → the scan dispatches a single `repository_dispatch`
(`ai-risk-guard-validate`) covering all captured jobs → the runner checks out the
workflow repo, runs the real `Sandbox` (`ci/validate.py run`) exactly as the App
would, and POSTs results back → the App stores them, triggers a re-analysis
(no local Docker needed), and the PR comment/check are updated with the runtime
evidence (marked "validated by CI runner"). While CI jobs are in flight, the
deferred re-validation worker waits for their results instead of re-running.

### LLM-readable regression explanation

Every finding card used to repeat the same technical regression-test block (test
counts, pinned test names, mocked env vars, rebind info). When Gemini is
available, the App now replaces that block in each card with one readable,
plain-language paragraph generated per distinct test payload (deduplicated, one
LLM call per file). The full technical detail stays available collapsed once per
file under **🧪 Regression test details** in the Patch & Validation section. When
Gemini is unavailable or rate-limited, the report fails open to the exact
deterministic block. Configure via the `regression_explain` section in
`config/app.yaml`.

Operational notes:
- The sandbox image is pre-built in the background at startup when Docker is up
  but the image is missing, so first scans don't pay the pull/build cost.
- Keep Docker healthy (e.g. `restart: unless-stopped` for the Docker service or
  containerized app) to minimize fail-closed scans.
- Monitor `ai_risk_guard_sandbox_fail_closed_total` and
  `ai_risk_guard_sandbox_available` in the Prometheus `/metrics` endpoint to
  alert on Docker outages.

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
