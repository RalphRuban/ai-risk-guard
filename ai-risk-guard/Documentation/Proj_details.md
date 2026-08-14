# AI Risk Guard - Complete Project Details

**Document**: Project Specification & Technical Reference  
**Version**: 3.0 (Multi-Agent Enterprise + CI/CD)  
**Status**: ✅ Production Ready  
**Last Updated**: 2026-08-09

---

## 📌 Executive Summary

**AI Risk Guard** is an autonomous multi-agent security orchestration platform integrated with GitHub. It detects 10 Python vulnerability types using AST + regex analysis, generates deterministic and LLM-enhanced patches via a Gemini model fallback chain (Gemini 2.5 Flash → 1.5 Flash → 2.0 Flash Lite), validates fixes in a hardened Docker sandbox (with a local fallback), enforces organizational security policy, uploads findings to GitHub Code Scanning via SARIF, and makes risk-aware autonomous gating decisions on GitHub PRs.

**Vision**: Transform GitHub security workflows by automating vulnerability detection, intelligent patching, risk assessment, policy enforcement, and continuous learning from patch outcomes.

**Target Users**:
- Development teams (GitHub users)
- Security engineers
- DevOps/SRE teams
- Organizations seeking automated security scanning

---

## 🎯 Project Status

### TIER 1: Core Features ✅
- ✅ Vulnerability Detection (10 types — AST + regex)
- ✅ Patch Generation (Deterministic AST Fixers + Gemini LLM + quality scoring)
- ✅ Hardened Sandbox Validation (Docker + local fallback + caching)
- ✅ Multi-Factor Risk Engine (8 weighted factors + policy escalation)

### TIER 2: High-Impact Features ✅
- ✅ GitHub PR Integration (Webhook / Reporter / Checks / SARIF)
- ✅ Diff-Aware Scanning (`is_new` tagging for PR gating)
- ✅ Confidence Scoring (Adaptive + historical learning engine)
- ✅ Contextual Risk Analysis (context validation + false-positive filtering)

### TIER 3: Advanced Features ✅
- ✅ **Autonomous Multi-Agent Mesh**: Scanner, Patch, Validator, Risk, Orchestrator + Manager agents
- ✅ **Multi-Candidate LLM Patching**: Gemini fallback chain generates context-aware candidates
- ✅ **Self-Improving Feedback Loop**: Learning via GitHub Reactions (🚀) + PR merges + SARIF dismissals
- ✅ **CWE/OWASP Mapping + SARIF 2.1.0**: Automatic industry-standard tagging with Code Scanning upload
- ✅ **Test Execution & Validation**: Auto-discovers test files, rebinds imports, runs `pytest` in sandbox

### TIER 4: Productization ✅
- ✅ **Professional Visual Dashboard**: React 18 + Vite SPA with real analytics and Light/Dark theme
- ✅ **Security Policy Engine**: Centralized YAML governance (`config/policy/default.yaml`) with mandatory sanitizers/wrappers
- ✅ **Autonomous Gating**: Risk-aware "Request Changes" decisions on GitHub
- ✅ **CI/CD**: GitHub Actions running pytest + ruff + mypy + frontend build
- ✅ **Operationally Observable**: Prometheus metrics, SARIF Code Scanning alerts, power: `waitress`

---

## 🏗️ System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│ GitHub (Event Source)                                                   │
│ • PR created/synchronize/reopened webhook                               │
│ • Installation events, reactions, PR merges/closed                      │
└────────────────────┬────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Flask Server (app/app.py → waitress, port 8000)                         │
│ • HMAC-SHA256 webhook signature verification (X-Hub-Signature-256)      │
│ • Webhook dedup (TTL 300s), ThreadPoolExecutor (max 3 concurrent)        │
│ • Token caching and OAuth session management (auto-refresh)              │
│ • 30+ REST API routes (dashboard, repos, scans, findings, metrics)       │
└────────────────────┬────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ ManagerAgent (app → core/agents/manager_agent.py)                       │
│  Fresh agent instances per file (thread-safe pipeline)                  │
│                                                                          │
│  1. SCANNER AGENT — vulnerability detection + test discovery            │
│  2. PATCH AGENT   — deterministic AST fixers + LLM candidates          │
│  3. VALIDATOR AGENT — syntax → sandbox (Docker/local) → rescan → policy│
│  4. RISK AGENT    — quality scoring, policy, confidence, risk, evidence│
│  5. ORCHESTRATOR  — executive decision + labels + SARIF                │
└────────────────────┬────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Outputs                                                                  │
│ • PR comment (hybrid report: New vs Legacy sections)                    │
│ • GitHub decision (COMMENT vs REQUEST_CHANGES)                          │
│ • Risk-prefixed PR labels (security-risk-N)                             │
│ • SARIF 2.1.0 upload → GitHub Code Scanning                              │
│ • SQLite persistence + Prometheus metrics                               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Complete Workflow

```
1. GitHub sends POST /webhook (pull_request: opened/synchronize/reopened)
   or installation / reaction / PR closed events.
2. Flask verifies HMAC-SHA256 signature; dedupe via 300s TTL.
3. Extract repo_name, PR number, install_id; upsert repo from payload.
4. Submit to ThreadPoolExecutor (background) → returns 202 immediately.
5. Background worker (zero-copy ingestion, no disk clone):
   a. Fetch PR files via GitHub API (paginated).
   b. For each modified target file:
      - Fetch full content (network), write to TempDir.
      - ManagerAgent.process_file(): Scanner → Patch → Validator → Risk
        (per-file agent instances).
   c. Test file discovery + dependency fetch via test_file_fetcher;
      rebind test imports and stage deps on disk.
   d. Concurrency: per-file scans run in safety-scoped threads.
6. OrchestratorAgent computes worst risk across NEW actionable findings:
   - max_risk >= auto_request_changes_above (4.0) → REQUEST_CHANGES
   - max_risk >= max_allowed_risk (8.5)          → REQUEST_CHANGES
   - silent findings (DEBUG_CODE, TLS) never gate.
7. Post PR comment (65 KB truncation-safe) + SARIF upload in parallel.
8. Persist scan, findings, feedback, dashboard metrics; clear caches as needed.
9. Dashboard/metrics update on next load; reaction/merge events write feedback.
```

---

## 📦 Component Breakdown

### Agent Mesh (`core/agents/`)

```
├── base_agent.py          Abstract BaseAgent (std logging/metrics)
├── manager_agent.py       ManagerAgent — shared context builder + per-file pipeline, thread-safe
├── scanner_agent.py       ScannerAgent — scanner + caches + diff-aware
├── patch_agent.py         PatchAgent — AST baseline + LLM candidates
├── validator_agent.py     ValidatorAgent — PatchValidator/Sandbox/Rescanner/SSRF verify
├── risk_agent.py          RiskAgent — quality, policy, confidence, priority, risk
└── orchestrator_agent.py  OrchestratorAgent ("Executive" gating decision; also generates SARIF)
```

---

#### SCANNER (`core/scanner/`)

```
├── vulnerability_scanner.py   Phase-2 AST scanner — 10 vuln types + diff-awareness + metadata context
├── diff_engine.py             DiffAwareScanner.parse_diff between old/new code
├── context_validator.py       False-positive reduction (test/comment/placeholder/env-var)
└── test_file_fetcher.py       Discover + fetch test files & deps (GitHub raw/code commits, package-aware)
```

**Covers**: COMMAND_INJECTION, CODE_INJECTION, HARDCODED_SECRET, INSECURE_DESERIALIZATION, SQL_INJECTION, PATH_TRAVERSAL, SSRF, WEAK_CRYPTOGRAPHY, TLS_VERIFICATION_DISABLED, DEBUG_CODE.

---

#### PATCH (`core/patch/`)

```
├── fixers.py               ast.get_source_segment fuzzy match + SUPPORTED_FIXER_TYPES + apply_patch_to_content
├── llm_patcher.py          Gemini fallback chain + retry/backoff + rate-limit semaphore + SHA256 prompt cache
└── patch_orchestrator.py   apply_patches_safely — line-descending, used_lines conflict tracking
```

#### VALIDATOR (`core/validator/`)

```
├── patch_validator.py      validate_ast, validate_imports (dangerous imports; DANGEROUS_IMPORTS),
│                           validate_policy, validate_ssrf
├── sandbox.py              Hardened Docker sandbox + local fallback; BLOCKED_PATTERNS; SandboxCache; temp isolation
├── security_rescan.py      SecurityRescanner — re-scan after patch (success=False if still vulnerable)
└── test_rebind.py          rebind_test_imports — rewrite tests/ package imports to module under validation
```

Sandbox hardening (Docker):
- CPU 0.5, memory 512m, pids_limit 32, `network: none`, `read_only: true`
- `tmpfs /tmp:rw,noexec,nosuid,size=64m`, cap_drop `ALL`, `no-new-privileges`
- Code timeout 10s (`test_timeout_seconds` 60), output truncated 64 KB/256 KiB
- Non-root `sandboxuser`; blocked patterns; local fallback (+`setrlimit` on Linux) with `strip_secrets: true`

#### QUALITY, RISK & CONFIDENCE (`core/quality|risk|confidence/`)

```
quality/    patch_scorer.py    PatchScorer — 6 weighted factors (syntax, security, tests, complexity, format, confidence)
risk/       risk_engine.py     RiskEngine — 8 weighted factors + severity normalization + gating thresholds
            context_engine.py  Context-aware adjustments
            metrics_extractor.py Code complexity metrics
confidence/    confidence.py   BASE_CONFIDENCE per type + env-aware adjustments (docker/sandbox/test)
            learning_engine.py Time-weighted decay (30d half-life), MIN_SAMPLES=5, feedback stats query
```

#### POLICY (`core/policy/`)
```
└── policy_engine.py          PolicyEngine — loads config.policy; check_compliance; enforce_sanitizers; apply_policy
```
Enforcement rules (YAML-driven in `config/policy/default.yaml`):
- forbidden modules, forbidden functions (os.system/popen/eval/exec/hashlib.md5/sha1)
- mandatory sanitizers (`subprocess.run/Popen … shell=False`), sensitive paths (`auth/`, `secrets/`, …)
- restricted fn args (`hashlib.new` md5/sha1/md4/sha), mandatory SSRF wrappers (`validate_url_ssrf` for requests/urllib/httpx)
- path traversal wrappers (`os.path.basename`, `safe_path_join` for `open`)
- forbidden assignments, mandatory parameterized queries (package vs f-string/%); policy import-time config

#### SARIF (`core/sarif/`)
```
├── converter.py        findings_to_risk_assessments, build_analysis_summary, build_analysis_result
├── sarif_generator.py  SARIF 2.1.0 generator (severity map, CWE/OWASP/compliance, commit-SHA metadata)
└── sarif_writer.py     SARIFWriter for GitHub Code Scanning
```

#### CACHE (`core/cache/`) — SQLite-backed
├── scan_cache.py       per-file cache (content hash → scan output) — avoids repeat scans
├── gemini_cache.py     SHA256→JSON for prompt→output
├── test_file_cache.py  GitHub-blob based fetch cache, TTL
├── ast_cache.py        pickled AST trees (safe RestrictedUnpickler)
└── sandbox_cache.py    in-process dict

#### LLM (`core/llm/`)
- `model_resolver` for quality-ordered fallback chain (gemini-3.5-flash → gemini-3.6-flash → gemini-3.5-flash-lite → gemini-3.1-flash-lite); prompt-SHA-256 cache; sanitized prompt handling in `llm_patcher.py`.

#### EXCEPTIONS (`core/exceptions/`)
ScanError, PatchError, ValidationError, SandboxError, RiskAnalysisError, CacheError, ResourceCleanupError, InputValidationError (all under `AIRiskGuardError`).

#### CONFIG (`core/config/`)
- Pydantic v2 models: AppConfig, PolicyConfig, RiskConfig, QualityConfig, SandboxConfig (+ nested), `ConfigRegistry` lazy-load from `config/*.yaml`.

---

## 🎨 Data Models (Pydantic v2)

### Vulnerability (`core/models/vulnerability.py`)
```python
class VulnerabilityType(Enum):
    COMMAND_INJECTION, CODE_INJECTION, HARDCODED_SECRET,
    INSECURE_DESERIALIZATION, SQL_INJECTION, PATH_TRAVERSAL,
    SSRF, WEAK_CRYPTOGRAPHY, TLS_VERIFICATION_DISABLED, DEBUG_CODE

class Severity(Enum): HIGH | MEDIUM | LOW

class Vulnerability(BaseModel):
    type: VulnerabilityType
    file, line, code, severity, message,
    description, cwe, owasp, is_new: bool,
    function: str | None, context_lines: list | None
```

Other models: `analysis`, `patch` (PatchSource AST/LLM, PatchCandidate, PatchResult), `risk` (RiskFactor, CodeMetrics, RiskAssessment), `scan` (ScanResult with `success` + ISO timestamps), `validation` (SyntaxValidationResult, SandboxResult, RescanResult, ValidationResult).
Models coerce; reporter/SARIF reads both Pydantic (via `generate_sarif`) and dict interfaces.

---

## 🔐 Vulnerability Types Covered

All 10 types (from `core/metadata/vuln_metadata.py`): Rule IDs — **CMD001, EXEC001, SECRET001, SQL001, DESER001, PATH001, SSRF001, CRYPTO001, DEBUG001, TLS001**.

| # | Type (Vuln Name) | Example | Fix Strategy | Severity | CVSS-like |
|---|-------------------|---------|--------------|----------|-----------|
| 1 | COMMAND_INJECTION | `os.system(user_input)` | `subprocess.run(shlex.split(...), shell=False)` | HIGH | 9.5 |
| 2 | CODE_INJECTION | `eval(user_input)` | `ast.literal_eval()` | HIGH | 9.5 |
| 3 | HARDCODED_SECRET | `PASSWORD = "…"` | env-var / `os.getenv` | HIGH | 8.0 |
| 4 | INSECURE_DESERIALIZATION | `pickle.loads(data)` | `json.loads` | HIGH | 8.0 |
| 5 | SQL_INJECTION | `execute(f"…{id}")` | parameterized tuple binding | HIGH | 9.0 |
| 6 | PATH_TRAVERSAL | `open("/uploads/"+f)` | `os.path.basename()` / safe_path_join | HIGH | 7.0 |
| 7 | SSRF | `requests.get(user_url)` | `validate_url_ssrf()` | HIGH | 7.0 |
| 8 | WEAK_CRYPTOGRAPHY | `hashlib.md5(data)` | `hashlib.sha256()`/policy governed | MEDIUM | 5.0 |
| 9 | TLS_VERIFICATION_DISABLED | `verify=False` | force True (informational) | LOW | — |
| 10 | DEBUG_CODE | `breakpoint()`/`pdb` | remove (informational) | LOW | — |

> `DEBUG_CODE` `TLS_VERIFICATION_DISABLED` are **silent findings** — they never gate a PR decision.

---

## 🧩 Agent Mesh Details

### Manager Agent
- Builds a per-context `{file_path, pr_context, diff_data, repo_root, …}`; constructs fresh `ScannerAgent`, `PatchAgent`, `ValidatorAgent`, `RiskAgent` per file (thread-safety); `process_file()` executes the full chain.

### Scanner Agent
- Wraps `VulnerabilityScanner`, `ScanCache`, `DiffAwareScanner`; validates inputs via `core.utils.validation` (`validate_file_path`, `validate_diff_data`, `validate_code_input`, safe extensions). Discovers test files via `test_file_fetcher` (predict → fetch → dependent deps).

### Patch Agent
- Produces `"baseline_ast"` deterministic patch first; then `LLMPatcher` candidates; `PatchCache`; gates on policy (`enforce_sanitizers`, forbidden modules/functions/assignments, parameterized queries).

### Validator Agent
- Runs `PatchValidator` (AST/syntax, imports validity), `Sandbox` (execution), `SecurityRescanner` (re-scan), SSRF patch verification, then policy compliance. Parallel candidate validation via `ThreadPoolExecutor`.

### Risk Agent
- Applies `PolicyEngine`, `PatchScorer` (6 quality weights incl. negative complexity reward), `compute_confidence`, `compute_priority`, `generate_evidence`, `compute_risk` + `explain_risk`.

### Orchestrator Agent
- "Executive": gates on NEW-only actionable findings (silent excluded) using `auto_request_changes_above` (4.0) and `max_allowed_risk` (8.5). Sets PR labels (`security-risk-N`) and attaches SARIF. Complies with `skip_if_all_dismissed`.

---

## 🛠️ Technology Stack

### Core Languages
- **Python 3.13+** (backend — Flask, click, sandbox)
- **JavaScript** (React 18 + Vite 5 SPA)
- **SQL** (SQLite), **YAML** (config), **Docker** (sandbox)

### Key Libraries
| Category | Libraries | Purpose |
|----------|-----------|---------|
| **Web** | Flask, waitress | Webhook + API + SPA serving |
| **AST** | `ast`, `ast.get_source_segment` | Detection + patch transformation |
| **GitHub** | PyJWT, requests | Auth/JWT, API, Code Scanning |
| **LLM** | google-genai | Gemini fallback chain patching |
| **Data** | pydantic v2, numpy | Models + cyber validation |
| **Config** | PyYAML, pydantic | Pydantic models from config |
| **Testing** | pytest, hypothesis, pytest-mock | 550+ unit/feature tests + property tests |
| **Frontend** | React, Vite, Tailwind, Chart.js, framer-motion | SPA dashboard |
| **Ops** | prometheus_client, waitress, docker, psutil | Metrics, HTTP (waitress), sandbox runtime |

### Frontend Design System
- **React 18 + Vite 5** (dev port 3000; proxy `/api → :8000`; build into `../static/frontend`)
- **Tailwind CSS** scaffold + **custom CSS-variable design tokens** in `src/index.css`
- Three-pillar color zones: **Blue** (`#155EEF/#3B82F6` — tech/primary), **Red** (`#E11D48/#F43F5E` — energy/critical), **Silver** (`#A8B0BC/…` — data/structure)
- Component classes: `enterprise-card`, `card-blue|red|silver`, `.stat-icon`, `.eyebrow`, `.k-title`, `.k-sub`, `.btn-primary|accent|critical|outline|secondary`, `.badge` (ok/warn/blue/red), `.input-field`, `.stat-heading`, `.stat-label`, `.chart-label`
- Chart.js 4 + react-chartjs-2 (`Bar` + `Doughnut`); framer-motion for reveal + AnimatePresence

---

## 🌐 Frontend Pages & Routes

> SPA served by Flask at `/` (production build → `../static/frontend`).

| Route | Page | Auth | Purpose |
|-------|------|------|---------|
| `/` | Landing | public | Cinematic hero + marketing form |
| `/pipeline` | Pipeline | public | Visual 5-stage pipeline map |
| `/login` | Login | public | GitHub OAuth entry |
| `/docs` | Docs | public | Getting-started docs |
| `/status` | Status | public | Live health (DB/Gemini/Sandbox) |
| `/dashboard` | Dashboard | required | KPI cards, donut/bar charts, Needs-Attention |
| `/policy` | Policy | required | See enforced policy + raw YAML |
| `/repositories` | Repositories | required | Grid index (search, counts) |
| `/repositories/:repoId` | RepositoryDetail | required | Charts + findings table + patch feedback |
| `/scan/:scanId` | ScanDetail | required | Full PR report + per-finding feedback |
| `/findings` | FindingsExplorer | required | Cross-repo triage + filters + actions |
| `/scans` | Scans | required | "Pull Requests" table |
| `/metrics` | Metrics | required | Prometheus KPI + agent/sandbox tables |
| `/settings` | Settings | required | Profile, installs, scan_mode, network, repos |

---

## 🔑 GitHub & OAuth

- **App-only** discovery: repos come from webhook payloads/installations, no GitHub API repo scan.
- **JWT**: GitHub App JWT (exp 540s, raw PEM or path) → installation access tokens
- **Install token auto-refresh** (55-min lifecycle); OAuth access token auto-refresh via refresh-token
- **OAuth login**: GitHub App OAuth, no passwords. `/auth/callback` exchanges code; `get_user_installations`. Session stores github_id + tokens; `upsert_user` + installations table.
- **Webhook auth**: `X-Hub-Signature-256` HMAC-SHA256; installation/repo events
- **Reporter**: collapsible finding cards, `BOT_MARKER` comments, duplicates cleanup, `_RETRY_KWARGS` (3 retries + backoff + Retry-After), `set_pr_labels`.
- **SARIF**: uploads to Code Scanning (gzip+base64; ref `refs/pull/N/head`); handles 202/422/429, polls status, reconciles all dismissed alerts.

---

## 💾 Database (SQLite — `utils/db.py`)

Tables: `dashboard` (key/value stats), `users`, `user_installations`, `user_settings`, `repos`, `scans`, `findings` (scan_id, vuln_type, severity, risk, file, line, is_new, status open/resolved/dismissed), `pr_findings` (PR-level join), `patch_feedback` (per-user feedback with dedup).
SQLite-backed caches: `scan_cache`, `gemini_cache` (SHA256 → output), `test_file_cache` (GitHub-blob based, TTL 86400s), `ast_cache` (pickled AST trees, safe `RestrictedUnpickler`); `sandbox_cache` is an in-process dict.
Key functions: `get_dashboard, increment_dashboard`, `upsert_user/repo`, `get_repos/get_scans`, `record_scan/record_finding`, `get_findings/update_finding_status`, `get_feedback_stats/records`, `resolve` helpers, `record_feedback`.

---

## ✅ Test Suite

> `python -m pytest tests/ -x -q`

20 test modules cover ~552 tests, incl.:

| Module | Focus |
|--------|-------|
| `test_core.py` | 10 vuln types, AST metadata, severity |
| `test_features_345.py` | Vuln types + sanitizers + parse diff |
| `test_fixes_verification.py` | Fixer correctness, AST determinism |
| `test_orchestrator.py` | Gating, silent-type exclusion, decision |
| `test_patch_agent.py` / `test_patch_validator.py` | AST/import/policy/SSRF validation |
| `test_policy.py`, `test_policy_engine*` | forbidden lists, sanitizers, wrappers, queries |
| `test_risk*.py` | Average/max/max-risk, security score boundaries |
| `test_reporter.py` | Comment format/truncation/bot-comment update |
| `test_github.py` | JWT/OAuth install flow |
| `test_sarif.py` | SARIF 2.1.0 generator |
| `test_metrics.py` | Prometheus metrics/endpoints |
| `test_gemini_cache.py`/`test_llm_patcher.py` | LLM caching, retry, fallback |
| `test_ast_cache.py`, `test_cache` | Cache layer, restricted build |
| `test_test_fetcher.py` | Test-discovery + dependency fetch |
| `test_test_rebind.py` / `test_test_file_cache.py` | Import rebind, blob TTL cache |
| `test_retry.py` | 429/backoff retry behaviour |
| `test_webhook_e2e.py` | Webhook → pipeline status |
| `conftest.py` | pytest fixtures, mock Gemini/Resolver |

---

## 🔌 API Endpoints (app/app.py)

| Method | Route |
|--------|-------|
| POST | `/webhook` |
| GET | `/api/health` , `/api/metrics/prometheus` |
| GET | `/api/policy` |
| GET | `/api/settings` (POST) |
| GET | `/api/health/gemini`, `/api/health/db`, `/api/health/sandbox` |
| GET | `/api/dashboard`, `/api/repos`, `/api/repos/<id>`, `/api/repos/<id>/scans`, `/api/repos/<id>/findings` |
| GET | `/api/scans`, `/api/scans/<id>`, `/api/scans/<id>/findings` |
| GET | `/api/findings` (filters/limit) |
| POST | `/api/findings/<id>/status` (resolve/dismiss) |
| POST | `/api/feedback`, `/feedback` |
| GET | `/auth/login`, `/auth/callback`, `/auth/logout`, `/api/me` |
| GET | `/dashboard`, `/` (SPA) |

---

## 🚀 Deployment

### CI/CD (GitHub Actions — `.github/workflows/ci.yml`)
- Python 3.13 on Ubuntu: `ruff` lint → `mypy` type-check → `pytest -q`
- Node 20: `npm ci` + `npm run build` (Vite)

### Serve
`python app/app.py` — **waitress** on `0.0.0.0:8000` (configurable via `PORT`); SPA served by Flask. Docker optional for sandbox (docker image `ai-risk-guard:sandbox`, local fallback for dev).

### Config files
- `config/app.yaml` (server, webhook via `max_concurrent_analyses=3`, logging, sarif, llm fallback chain)
- `config/risk.yaml` (weights, gating 8.5/4.0), `config/quality.yaml`, `config/policy/default.yaml`, `config/sandbox.yaml`

---

## 📈 System Metrics (Prometheus)
`app/metrics.py` — counters/gauges/histograms:
- `scan_total`, `scan_duration` (ms), `vulnerabilities_total`, `vulnerabilities_active`, `patches_total`, `APP_INFO`
- Exposed at `/api/metrics/prometheus`

---

## 🔒 Security Considerations

| Area | Measure |
|------|---------|
| Webhook auth | HMAC-SHA256 (`X-Hub-Signature-256`), dedup, sessions signed |
| GitHub API | scoped installation tokens, JWT (RSA), refresh handling |
| Sandbox | Docker (ro filesystem, no network, cap-drop, pids/memory/CPU/time limits), local fallback with `setrlimit` + `strip_secrets`, mock tests/time functions |
| LLM | Prompt SHA-256 caching, sanitized prompt code (`strip_secrets` in env, redacts keys/IPs where applied) |
| Policy | Centralized YAML guardrails: forbidden modules/functions, allowed sanitizers, SSRF wrappers, path traversal wrappers, parameterized queries |
| Response | SARIF upload (only new findings), PR labels, bot-comment updates, Retry/backoff, tests separate risk gates |
| Dashboards | OAuth-gated; CORS only when `FRONTEND_ORIGIN` set |

---

## 📈 Scalability

**Current**: Single waitress worker, ThreadPoolExecutor (3), SQLite (WAL journal, background write), in-proc + SQLite caches; minimal GitHub API usage (targeted, phase-based fetches).
**Planned / Growing**: Postgres for live load, Redis caches, queue-based fan-out (Celery), metrics scaling, more output channels (SARIF → Jira, etc.), multi-repo telemetry.

---

## 🧠 Learning & Confidence

- `calculate_confidence` (in `confidence.py`): per-type `BASE_CONFIDENCE`, adjusted by validation success (+0.1 / −0.25), HIGH severity (+0.03), test results (docker +0.12 / local +0.06 / other +0.04), quality score (×0.08), patch-length penalties (+<10 → −0.1, >400 → −0.15), clamped to [0,1].
- `ConfidenceLearningEngine` (in `learning_engine.py`): time-weighted decay (30-day half-life), minimum sample size (default 5), queries `get_feedback_stats/get_feedback_records` and adjusts by the ACCEPTED rate: ≥90% → +0.10, ≥75% → +0.05, ≤25% → −0.15, ≤40% → −0.05, else 0.0.
- Feedback written on GitHub **rockets (🚀)**, `-1`/`+1` reactions, PR merges and SARIF dismissals are consumed by `record_feedback` on `/api/feedback` and the webhook.

---

## 📚 Documentation

### User/Frontend
- [x] Landing with GitHub OAuth
- [x] Docs page (Getting Started, env ref, pipeline diagram, sandbox, policy, FAQ)
- [x] Status page (live health)
- [x] Pipeline page (visual 5-stage)
- [x] Settings (profile, installs, scan_mode, sandbox network)
- [x] README (setup, config, run, deployment link)

### Technical
- [x] Architecture overview (`ARCHITECTURE_OVERVIEW.md`)
- [x] Component dependency map (`COMPONENT_DEPENDENCY_MAP.md`)
- [x] Navigation map (`NAVIGATION.md`)
- [x] Visual reference (`VISUAL_REFERENCE_GUIDE.md`)
- [x] README (setup, config, run, deployment, env vars)
- [ ] Deployment guide for heavy production (may be extended)

### Dev Ops
- [x] CI (pytest + ruff + mypy + frontend build)
- [x] Docker sandbox image + local fallback
- [ ] Multi-language support
- [ ] Scale-out deployment, multi-tenant install subscriptions

---

## 🎬 Success Story

**Day 1**: Developer pushes a PR with `os.system(user_input)` + `pickle.loads(data)` + hardcoded `API_KEY`.

1. Webhook → HMAC verify → repo upsert, thread scheduled.
2. ScannerAgent finds 2 new vulns; PatchAgent builds AST baseline + Gemini patch.
3. Validator runs Docker sandbox (RO, no network) + pytest test re-binding + re-scan.
4. RiskAgent → 8-factor score (e.g. 7.8); PolicyEngine flags attempts (os.system, hardcoded secret) → gate REQUEST_CHANGES.
5. Orchestrator posts PR comment, sets `security-risk-7` label, uploads SARIF case to Code Scanning.
6. Dev applies fix; re-scan clean; auto-feedback via reaction updates confidence.

---

## 💰 Business Value

### Users
- Rapid detection of 10 vuln classes (fully automated scan)
- Deterministic AST fixes plus LLM innovation with quality scoring
- Clear decision context: PR-level risk flows, risk labels, SARIF in GitHub
- PR comment includes exact patched code + validation summary

### Orgs
- Enforced policy, risk-gate thresholds, GitHub Code Scanning results
- Risk + quality + confidence + SARIF compliance reporting
- Metrics and telemetry; no unsanctioned deviation from standards

---

## 🏆 Differentiation

1. **Hybrid deterministic + LLM patching** with quality-aware candidate ranking.
2. **Real hardened sandbox + test-program execution** (Docker/fallback; pytest in image).
3. **YAML-driven enterprise policy engine** (SSRF urls, open wrappers, `shell=False`, forbidden lists, parameterized queries).
4. **SARIF 2.1.0 → GitHub Code Scanning** with `skip_if_all_dismissed` reconciliation.
5. **Operationally-observable** (Prometheus, system app page, health endpoints).
6. **Threat-model-aware**: silent findings categorized, diff-gated positive reviews, learning engine, feedback loops.

---

## 📋 Status Check

### ✅ Completed
- 10 vulns + diff-aware scanning
- AST + Gemini patch generation w/ quality tier
- Hardened Docker + local sandbox, test execution
- Full policy engine (YAML-driven)
- 8-factor risk + gating
- GitHub OAuth, webhook, comments, labels, SARIF
- React SPA dashboard (Dark/Light, 3-pillar design system)
- Agent mesh (manager + 5 agents), thread-safe per-file
- 550+ tests, CI/CD workflow
- SQLite schema + multiple caches + Prometheus metrics

### ⚠️ Known limitations
- Local (no-docker) fallback executes code with reduced isolation (still strip-secrets + timeouts/limits).
- Docker best-effort only when binary present (`build_local_image` requires network/docker-socket).
- SQLite single-node; concurrent write scaling may need Postgres/Redis.
- `GEMINI_API_KEY` optional — falls back to AST-only patching if absent.

### 📝 Roadmap
- Postgres + Redis, Celery/queue fan-out
- Multi-language detection (JS/Java/Go), batched test running CI
- Per-org policy UIs / multi-tenant enforcement
- Signed-artifact replay proof (non-determinism / TEE sandbox)
- SAST for additional ecosystems; GitHub-Check-Runs-driven block (e.g., required status checks)

---

## 🎯 Conclusion

**AI Risk Guard** is a **production-ready autonomous security automation platform**: multi-agent mesh, hybrid deterministic+LLM patching, hardened sandbox with tests, YAML policy engine, SARIF Code Scanning integration, OAuth GitHub app, React dashboard design system, and 550+ tests in CI. It is a reliable, extensible security gate for modern Python teams.