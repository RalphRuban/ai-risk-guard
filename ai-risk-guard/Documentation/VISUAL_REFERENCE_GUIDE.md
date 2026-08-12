# AI Risk Guard - Visual Reference Guide

## Module Inventory

```
ai-risk-guard/
│
├── app/                           # Application Layer
│   ├── main.py                    ✅ AIRiskGuard (main orchestrator)
│   ├── app.py                     ✅ Flask webhook + OAuth + REST API + SPA
│   └── metrics.py                 ✅ Prometheus metrics
│
├── core/
│   │
│   ├── config/                    # CONFIG LAYER (Pydantic v2)
│   │   ├── app_config.py          ✅ Server/webhook/llm/sarif
│   │   ├── risk_config.py         ✅ Risk weights + gating
│   │   ├── policy_config.py       ✅ Policy guardrails
│   │   ├── quality_config.py      ✅ Quality weights
│   │   ├── sandbox_config.py      ✅ Docker + local limits
│   │   └── __init__.py            ✅ ConfigRegistry singleton
│   │
│   ├── models/                    # DATA MODELS (Pydantic v2)
│   │   ├── vulnerability.py       ✅ VulnerabilityType (10) + Severity
│   │   ├── analysis.py            ✅ Analysis result
│   │   ├── patch.py               ✅ Patch candidates/results
│   │   ├── risk.py                ✅ RiskFactor/CodeMetrics/RiskAssessment
│   │   ├── scan.py                ✅ ScanResult
│   │   └── validation.py          ✅ Validation stage results
│   │
│   ├── agents/                    # AGENT MESH
│   │   ├── base_agent.py          ✅ Abstract base agent
│   │   ├── manager_agent.py       ✅ Pipeline orchestrator
│   │   ├── scanner_agent.py       ✅ Vulnerability scanning + test discovery
│   │   ├── patch_agent.py         ✅ AST + Gemini patch generation
│   │   ├── validator_agent.py     ✅ 5-stage validation
│   │   ├── risk_agent.py          ✅ Risk/quality/confidence/evidence
│   │   └── orchestrator_agent.py  ✅ GitHub decisions + labels + SARIF
│   │
│   ├── scanner/                   # SCANNING LAYER
│   │   ├── vulnerability_scanner.py ✅ Main scanner (10 vuln types)
│   │   ├── diff_engine.py         ✅ Diff-aware filtering
│   │   ├── context_validator.py   ✅ False-positive reduction
│   │   └── test_file_fetcher.py   ✅ Test file + dependency discovery
│   │
│   ├── patch/                     # PATCHING LAYER
│   │   ├── patch_orchestrator.py  ✅ Conflict-safe patch application
│   │   ├── fixers.py              ✅ AST patch engine (fuzzy match)
│   │   └── llm_patcher.py         ✅ Gemini fallback chain + cache
│   │
│   ├── validator/                 # VALIDATION LAYER
│   │   ├── patch_validator.py     ✅ Syntax/import/policy/SSRF validation
│   │   ├── sandbox.py             ✅ Docker sandbox + local fallback
│   │   ├── security_rescan.py     ✅ Re-scan patched code
│   │   └── test_rebind.py         ✅ Test import rebinding
│   │
│   ├── risk/                      # RISK ANALYSIS LAYER
│   │   ├── risk_engine.py         ✅ Weighted risk scoring (8 factors)
│   │   ├── context_engine.py      ✅ Context-aware adjustments
│   │   └── metrics_extractor.py   ✅ Code complexity metrics
│   │
│   ├── quality/                   # QUALITY LAYER
│   │   └── patch_scorer.py        ✅ 6-factor patch quality scoring
│   │
│   ├── confidence/                # CONFIDENCE LAYER
│   │   ├── confidence.py          ✅ Confidence scoring
│   │   └── learning_engine.py     ✅ Historical learning (time decay)
│   │
│   ├── policy/                    # POLICY ENFORCEMENT
│   │   └── policy_engine.py       ✅ YAML-driven security policy
│   │
│   ├── metadata/
│   │   ├── vuln_metadata.py       ✅ Rule IDs, severities, CWE/OWASP
│   │   └── versions.py            ✅ Version constants
│   │
│   ├── sarif/                     # SARIF OUTPUT
│   │   ├── converter.py           ✅ Findings → risk assessments
│   │   ├── sarif_generator.py     ✅ SARIF 2.1.0 generation
│   │   └── sarif_writer.py        ✅ SARIF writer
│   │
│   ├── cache/                     # CACHE LAYER (SQLite-backed)
│   │   ├── scan_cache.py          ✅ Per-file scan cache
│   │   ├── gemini_cache.py        ✅ LLM prompt cache (SHA256)
│   │   ├── test_file_cache.py     ✅ GitHub blob fetch cache (TTL)
│   │   ├── ast_cache.py           ✅ Pickled AST cache (safe)
│   │   └── sandbox_cache.py       ✅ In-proc sandbox cache
│   │
│   ├── llm/                       # LLM LAYER
│   │   └── model_resolver.py      ✅ Model fallback resolution
│   │
│   ├── exceptions/                # ERROR HIERARCHY
│   │   └── __init__.py            ✅ AIRiskGuardError + typed errors
│   │
│   ├── utils/                     # CORE UTILITIES
│   │   ├── tempdir.py             ✅ TempDir context manager
│   │   └── validation.py          ✅ Input validation (paths, diffs, code)
│   │
│   └── reporting/
│       └── explainer.py           ✅ Remediation explanations
│
├── services/
│   └── github/
│       ├── auth.py                ✅ JWT + installation tokens + OAuth
│       └── reporter.py            ✅ PR comments, labels, SARIF upload
│
├── utils/
│   ├── logger.py                  ✅ Structured JSON logging
│   ├── db.py                      ✅ SQLite persistence
│   └── retry.py                   ✅ Retry with backoff
│
├── frontend/                      # REACT SPA
│   ├── src/
│   │   ├── main.jsx               ✅ React entry (BrowserRouter)
│   │   ├── App.jsx                ✅ 14 routes
│   │   ├── index.css              ✅ Design tokens + component classes
│   │   ├── api/client.js          ✅ Axios API client
│   │   ├── components/            ✅ Navbar, Footer, Layout, PageHeader, ThemeToggle
│   │   ├── hooks/                 ✅ useCountUp, useScrollReveal
│   │   └── pages/                 ✅ 14 pages (Dashboard, Findings, Metrics, ...)
│   ├── vite.config.js             ✅ Dev :3000, proxy /api→:8000, build → ../static/frontend
│   └── tailwind.config.js         ✅ Custom palette + fonts
│
├── sandbox/
│   ├── Dockerfile.sandbox         ✅ python:3.10-slim + pytest + non-root
│   └── mock_header.py             ✅ Mock env + time.sleep patch
│
├── config/
│   ├── app.yaml                   ✅ App/server/webhook/llm/sarif
│   ├── risk.yaml                  ✅ Weights + gating thresholds
│   ├── quality.yaml               ✅ Quality weights
│   ├── sandbox.yaml               ✅ Sandbox limits
│   └── policy/default.yaml        ✅ Security policy guardrails
│
├── tests/                         ✅ ~550 tests across 20 modules
│   ├── conftest.py
│   ├── test_core.py, test_features_345.py, test_fixes_verification.py
│   ├── test_orchestrator.py, test_patch_agent.py, test_patch_validator.py
│   ├── test_policy*.py, test_risk*.py, test_reporter.py, test_github.py
│   ├── test_sarif.py, test_summary.py, test_metrics.py
│   ├── test_gemini_cache.py, test_llm_patcher.py, test_ast_cache.py, test_retry.py
│   ├── test_test_fetcher.py, test_test_file_cache.py, test_test_rebind.py
│   ├── test_webhook_e2e.py, demo.py, demo_test.py
│   └── ...
│
└── Documentation/                ✅ Updated to current implementation
```

---

## Status Legend

| Status | Meaning |
|--------|---------|
| ✅ | Active, tested, imported |
| ⚠️ | Unused or incomplete |
| 🔴 | Broken (critical bug) |

---

## Data Flow (Request → Response)

```
┌─────────────────────────────────────────────────┐
│ INPUT: PR Event from GitHub                     │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ app/app.py::github_webhook()                    │
│ • Verify X-Hub-Signature-256 (HMAC-SHA256)      │
│ • Dedup (300s TTL)                              │
│ • Extract repo, PR #, installation ID           │
│ • Upsert repo from payload                      │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ ThreadPoolExecutor (max 3) → background         │
│ Fetch PR files (paginated, no disk clone)       │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ ManagerAgent.process_file()                     │
│ (fresh agent instances per file)                │
└─────────────────────────────────────────────────┘
                      ↓
        ┌─────────────────────────┐
        │ PHASE 1: SCAN           │
        ├─────────────────────────┤
        │ File → AST Parse        │
        │ → VulnerabilityScanner  │
        │ → Regex secrets         │
        │ → DiffAwareScanner      │
        │ → ContextValidator      │
        │ → Test file discovery   │
        │ ↓                       │
        │ [Vulnerabilities]       │
        └─────────────────────────┘
                      ↓
        ┌─────────────────────────┐
        │ PHASE 2: PATCH          │
        ├─────────────────────────┤
        │ fixers (baseline_ast)   │
        │ llm_patcher (Gemini)    │
        │ apply_patches_safely()  │
        │ ↓                       │
        │ Patch candidates        │
        │ Unified diff            │
        └─────────────────────────┘
                      ↓
        ┌─────────────────────────┐
        │ PHASE 3: VALIDATE       │
        ├─────────────────────────┤
        │ • PatchValidator        │
        │ • Sandbox.run()         │
        │ • test_rebind + pytest  │
        │ • SecurityRescanner     │
        │ • PolicyEngine          │
        │ ↓                       │
        │ Validation results      │
        └─────────────────────────┘
                      ↓
        ┌─────────────────────────┐
        │ PHASE 4: ANALYZE        │
        ├─────────────────────────┤
        │ patch_scorer (quality)  │
        │ calculate_confidence()  │
        │ compute_risk()          │
        │ explain_risk()          │
        │ ↓                       │
        │ Risk (0-10) · Confidence│
        │ · Quality (0-1)         │
        └─────────────────────────┘
                      ↓
        ┌─────────────────────────┐
        │ PHASE 5: ACT / REPORT   │
        ├─────────────────────────┤
        │ Gating decision         │
        │ set_pr_labels()         │
        │ generate_sarif()        │
        │ format_report()         │
        │ upload SARIF + comment  │
        └─────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ OUTPUT: PR comment + risk label + SARIF result  │
└─────────────────────────────────────────────────┘
```

---

## Execution Paths

### PATH 1: CLI Usage
```
$ python app/main.py /path/to/file.py
                      ↓
          AIRiskGuard().analyze_file(file_path)
                      ↓
          Print formatted report to stdout
```

### PATH 2: GitHub Webhook
```
POST /webhook (from GitHub)
      ↓
verify_signature() + dedup
      ↓
Extract: repo_name, pr_number, access_token
      ↓
Fetch PR files via GitHub API (no disk clone)
      ↓
For each target file:
  ManagerAgent.process_file()
      ↓
Post PR comment + SARIF + labels
```

---

## Import Dependency Levels

### Level 1: Entry Points (Top)
```
app/main.py
app/app.py
```

### Level 2: Main Orchestrators
```
core/config (ConfigRegistry)
core/agents/manager_agent.py
core/agents/orchestrator_agent.py
services/github/reporter.py
```

### Level 3: Agent Pipeline Components
```
core/agents/scanner_agent.py, patch_agent.py, validator_agent.py, risk_agent.py
core/scanner/* (vulnerability_scanner, diff_engine, context_validator, test_file_fetcher)
core/patch/* (fixers, patch_orchestrator, llm_patcher)
core/validator/* (patch_validator, sandbox, security_rescan, test_rebind)
core/policy/policy_engine.py
core/sarif/* (converter, sarif_generator, sarif_writer)
services/github/auth.py
```

### Level 4: Utilities & Data
```
core/models/* (Pydantic v2)
core/metadata/vuln_metadata.py
core/cache/* (SQLite-backed)
core/llm/model_resolver.py
utils/logger.py (used by everyone)
utils/db.py
utils/retry.py
core/reporting/explainer.py
```

---

## Critical Paths (High-Traffic Dependencies)

```
core/config (ConfigRegistry)
  ↑ (configuration for all agents)
  │
  ├─ vulnerability_scanner.py
  │  ├─ context_validator.py
  │  ├─ diff_engine.py
  │  └─ test_file_fetcher.py
  │
  ├─ patch_orchestrator.py → fixers.py + llm_patcher.py
  │
  ├─ sandbox.py → patch_validator.py + test_rebind.py
  │
  ├─ risk_engine.py → patch_scorer.py + confidence.py
  │
  └─ reporter.py → core/sarif + auth.py
```

---

## Problem Zones 🔴⚠️

### CRITICAL
- None. All critical bugs resolved.

### KNOWN LIMITATIONS (non-blocking)
- Local (no-Docker) fallback has reduced isolation (no `setrlimit` on Windows)
- SQLite is single-node; concurrent write scale-out requires Postgres/Redis
- LLM candidates are non-deterministic (quality scoring ranks best-effort)
- `GEMINI_API_KEY` optional → AST-only mode

---

## Test Coverage Map

```
tests/ covers:

✅ Detection (10 vuln types)
   ├─ COMMAND_INJECTION, CODE_INJECTION, HARDCODED_SECRET
   ├─ INSECURE_DESERIALIZATION, SQL_INJECTION, PATH_TRAVERSAL
   ├─ SSRF, WEAK_CRYPTOGRAPHY, TLS_VERIFICATION_DISABLED, DEBUG_CODE

✅ Patch Engine (fixer correctness, AST determinism)
✅ Policy Engine (forbidden lists, sanitizers, wrappers, queries)
✅ Risk Engine (8-factor scoring, security score boundaries)
✅ Quality Scorer (6-factor)
✅ Confidence (scoring + learning engine)
✅ Orchestrator (gating, silent-type exclusion)
✅ Reporter (comment format/truncation, bot-comment update)
✅ GitHub (JWT/OAuth install flow)
✅ SARIF (2.1.0 generator)
✅ Metrics (Prometheus endpoints)
✅ Caches (ast, gemini, scan, test-file)
✅ LLM (fallback chain, retry, rate-limit)
✅ Test-fetcher / test-rebind / test-file-cache
✅ Retry (429/backoff)
✅ Webhook e2e (webhook → pipeline)
```

---

## Configuration Environment Variables

```
GITHUB_APP_ID
  └─ GitHub App ID for JWT generation

GITHUB_PRIVATE_KEY
  └─ PEM-format private key for signing JWTs (content or path)

GITHUB_WEBHOOK_SECRET
  └─ Webhook secret for HMAC-SHA256 signature verification

GITHUB_APP_CLIENT_ID / GITHUB_APP_CLIENT_SECRET
  └─ OAuth login for dashboard

GEMINI_API_KEY (optional)
  └─ LLM patching (falls back to AST-only)

DB_PATH (optional)
  └─ SQLite database path (default: data/dashboard.db)

PORT (optional)
  └─ Bind port override (default: 8000)

FLASK_SECRET_KEY, SESSION_COOKIE_SECURE, FRONTEND_ORIGIN
  └─ Session signing / HTTPS / CORS
```

YAML configs: `config/app.yaml`, `risk.yaml`, `quality.yaml`, `sandbox.yaml`, `policy/default.yaml` (loaded by `core/config`).

---

## Module Responsibility Matrix

| Module | Responsibility | Status |
|--------|---|---|
| core/config | Pydantic v2 config from YAML | ✅ |
| core/models | Typed data models | ✅ |
| vulnerability_scanner | Detect 10 vuln types | ✅ |
| diff_engine | Tag changed lines (is_new) | ✅ |
| context_validator | Reduce false positives | ✅ |
| test_file_fetcher | Discover/fetch test files | ✅ |
| patch_orchestrator | Conflict-safe patching | ✅ |
| fixers | AST transformations | ✅ |
| llm_patcher | Gemini candidates + cache | ✅ |
| patch_validator | Syntax/import/policy/SSRF | ✅ |
| sandbox | Docker + local execution | ✅ |
| test_rebind | Rebind test imports | ✅ |
| security_rescan | Re-scan patched code | ✅ |
| policy_engine | Enforce YAML policy | ✅ |
| patch_scorer | 6-factor quality | ✅ |
| risk_engine | 8-factor risk scoring | ✅ |
| confidence | Confidence scoring | ✅ |
| learning_engine | Historical learning | ✅ |
| sarif_generator | SARIF 2.1.0 output | ✅ |
| reporter | PR comments, labels, SARIF | ✅ |
| auth | GitHub JWT/OAuth | ✅ |
| logger | Logging infrastructure | ✅ |
| db | SQLite persistence | ✅ |
| retry | Backoff retry | ✅ |
| app.py (server) | Webhook + OAuth + API + SPA | ✅ |
| frontend | React 18 SPA (14 pages) | ✅ |

---

## Performance Hotspots

```
SCANNING (O(n) where n = file lines)
  ├─ AST parsing: ~1-2ms per file
  ├─ Context validation: ~5-10ms
  └─ Total: ~10-20ms per file

PATCHING (O(n*m) where n = vulns, m = avg complexity)
  ├─ Conflict detection: ~1ms per vuln
  ├─ AST transformation: ~5-10ms per vuln
  └─ Total: ~20-50ms per file (LLM candidates add latency)

VALIDATION (O(n*k) where k = validators)
  ├─ Syntax check: ~2-5ms
  ├─ Sandbox execution: ~100-500ms (depends on code; cached)
  ├─ Re-scan: ~15-25ms
  └─ Total: ~150-500ms per result

ANALYSIS (O(n))
  ├─ Risk scoring: ~1-2ms per vuln
  ├─ Confidence scoring: ~1-2ms per vuln
  └─ Total: ~5-10ms per result

Overall: ~200-600ms per file (AST-only) — LLM candidates add seconds.
```

---

## Webhook Processing Timeline

```
Event Received
  │
  ├─ Signature verification + dedup: 1-2ms
  │
  ├─ Fetch PR files (GitHub API, paginated): 100ms-2s
  │
  ├─ For each target file (avg 5-10 files in PR):
  │  ├─ Scan: 20ms
  │  ├─ Patch: 50ms (AST) / +3-8s (Gemini)
  │  ├─ Validate: 300ms (docker) / 100ms (cached)
  │  └─ Analyze: 10ms
  │  → Subtotal per file: ~380ms (AST-only)
  │
  ├─ Total for all files: ~2-5s (AST) / 30-90s (with LLM + tests)
  │
  ├─ Format report + SARIF: 10ms
  │
  ├─ Post PR comment + SARIF upload: 500-1000ms (GitHub API)
  │
  └─ Return 202 Accepted (immediate); results delivered async
```

---

## Repository Structure Health

```
✅ Good Practices:
  • Logical module organization (by concern)
  • Separation of concerns (scanner, patch, validator, risk, quality)
  • Central config (YAML → Pydantic) + typed models
  • Multi-layer caching (SQLite + in-proc)
  • Full test suite (~550) + CI/CD
  • Typed exceptions + input validation
  • Clear entry points (main.py, app.py, frontend)

⚠️ Areas for Improvement:
  • Scale-out: Postgres/Redis/Celery
  • Multi-language detection
  • Deterministic LLM output (temperature control / retry ranking)
  • Windows local fallback isolation (no setrlimit)

🔴 Critical Issues:
  • None.
```

---

## Next Immediate Actions

**Priority 1** (Operations):
1. Run `python -m pytest tests/ -x -q` + `ruff check .` + `mypy .` in CI
2. Verify frontend build (`cd frontend && npm run build`)
3. Review Prometheus metrics on a live scan

**Priority 2** (Scale):
1. PostgreSQL + Redis migration
2. Queue-based fan-out (Celery) for large PRs
3. Multi-language scanners (JS/Java/Go)

**Priority 3** (Product):
1. Per-org policy management UI
2. Required status-check / check-run gating
3. Deployment guide + screenshots gallery
