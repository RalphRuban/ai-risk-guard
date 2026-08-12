# AI Risk Guard - Architecture Overview

## Project Summary
**AI Risk Guard** is an autonomous multi-agent security orchestration platform integrated with GitHub. It detects 10 vulnerability types (command injection, code injection, SQL injection, path traversal, SSRF, hardcoded secrets, insecure deserialization, weak cryptography, TLS verification disabled, debug code), generates deterministic AST-based and LLM-enhanced patches via a Gemini fallback chain, validates fixes in a hardened Docker sandbox (with local fallback), enforces organizational security policy, uploads findings to GitHub Code Scanning via SARIF, and makes risk-aware autonomous gating decisions on GitHub PRs.

**Tech Stack**: Python 3.13+ | Flask + waitress | GitHub App (OAuth + App JWT) | SQLite | Pydantic v2 | AST/Regex Analysis | Gemini 2.5/1.5 Flash | Docker | Policy Engine | React 18 + Vite

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub (via Webhook + OAuth)                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│            Flask Server (app/app.py → waitress :8000)           │
│  • Verifies webhook signature (X-Hub-Signature-256, HMAC-SHA256) │
│  • Webhook dedup (300s TTL), ThreadPoolExecutor (max 3 workers)  │
│  • OAuth login (GitHub App, no passwords) + session refresh      │
│  • 30+ REST API routes (dashboard, repos, scans, findings, ...)  │
│  • Prometheus metrics + SPA serving (/ and /dashboard)           │
└───────────┬───────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│              ManagerAgent (core/agents/manager_agent.py)        │
│         Fresh agent instances per file (thread-safe)            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  MULTI-AGENT PIPELINE (5 executor agents + manager)     │   │
│  │                                                           │   │
│  │  1. SCANNER AGENT                                        │   │
│  │     └─ ScannerAgent → VulnerabilityScanner               │   │
│  │        ├─ AST analysis (10 vulnerability rules)          │   │
│  │        ├─ Regex secret scanning (non-Python configs)     │   │
│  │        ├─ Diff-aware filtering (is_new flag)             │   │
│  │        ├─ Context validation (false positive reduction)  │   │
│  │        └─ Test file discovery + dependency fetch         │   │
│  │                                                           │   │
│  │  2. PATCH AGENT                                          │   │
│  │     └─ PatchAgent                                        │   │
│  │        ├─ Deterministic AST patching (fixers.py)         │   │
│  │        ├─ LLM multi-candidate (Gemini fallback chain)    │   │
│  │        ├─ Conflict-safe orchestration                    │   │
│  │        └─ Policy-driven sanitizer enforcement            │   │
│  │                                                           │   │
│  │  3. VALIDATOR AGENT                                      │   │
│  │     └─ ValidatorAgent                                    │   │
│  │        ├─ Syntax & semantic checks (PatchValidator)      │   │
│  │        ├─ Sandbox execution (Docker / local fallback)    │   │
│  │        ├─ Test import rebind + pytest execution          │   │
│  │        ├─ Security re-scan (SecurityRescanner)           │   │
│  │        └─ Policy compliance (PolicyEngine)               │   │
│  │                                                           │   │
│  │  4. RISK AGENT                                           │   │
│  │     └─ RiskAgent                                         │   │
│  │        ├─ 8-factor weighted risk scoring                  │   │
│  │        ├─ 6-factor patch quality scoring (PatchScorer)   │   │
│  │        ├─ Confidence scoring + learning engine           │   │
│  │        ├─ Candidate ranking & winner selection            │   │
│  │        └─ Evidence generation + risk explanation          │   │
│  │                                                           │   │
│  │  5. ORCHESTRATOR AGENT                                   │   │
│  │     └─ OrchestrationAgent ("Executive")                  │   │
│  │        ├─ Autonomous GitHub decisions                    │   │
│  │        ├─ COMMENT / REQUEST_CHANGES gating               │   │
│  │        ├─ Risk-prefixed PR labels (security-risk-N)      │   │
│  │        └─ SARIF generation for Code Scanning            │   │
│  │                                                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│            Outputs (services/github/reporter.py)                │
│  • PR comment — hybrid report (New vs Legacy sections)          │
│  • GitHub decision + risk labels                                │
│  • SARIF 2.1.0 upload → Code Scanning (gzip+base64, polling)    │
│  • Auto-feedback via 🚀 reactions, PR merges, SARIF dismissals  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. **Multi-Agent Mesh** (`core/agents/`)

**Purpose**: Autonomous orchestration of the security pipeline via specialized agents.

| Agent | File | Responsibility |
|-------|------|----------------|
| `BaseAgent` | `base_agent.py` | Abstract base; standardized logging + duration metrics |
| `ManagerAgent` | `manager_agent.py` | Builds shared context; instantiates fresh agents per file for thread safety; `process_file()` end-to-end |
| `ScannerAgent` | `scanner_agent.py` | Delegates to `VulnerabilityScanner` + caches + `DiffAwareScanner`; discovers test files |
| `PatchAgent` | `patch_agent.py` | Generates candidates (AST `baseline_ast` + optional Gemini variants) |
| `ValidatorAgent` | `validator_agent.py` | Multi-stage validation: syntax, sandbox, re-scan, policy + SSRF verify |
| `RiskAgent` | `risk_agent.py` | Quality scoring, policy, confidence, priority, risk + evidence |
| `OrchestrationAgent` | `orchestrator_agent.py` | Executive GitHub decisions (COMMENT / REQUEST_CHANGES), labels, SARIF |

**Pipeline Flow**:
```
ManagerAgent.process_file()
    → ScannerAgent.execute()
        → ScannerAgent discovers test files (test_file_fetcher)
    → PatchAgent.execute()
        → AST patching + optional Gemini candidates
    → ValidatorAgent.execute()
        → syntax → sandbox → rescan → policy (per candidate)
    → RiskAgent.execute()
        → PatchScorer, policy, confidence, risk, evidence
    → OrchestrationAgent.execute()
        → gating decision + labels + SARIF
```

---

### 2. **Scanning Layer** (`core/scanner/`)

**Purpose**: Detect vulnerabilities using AST analysis, regex, and diff-awareness

| Module | Class | Role |
|--------|-------|------|
| `vulnerability_scanner.py` | `VulnerabilityScanner` | Main scanner; AST detection for 10 types + regex secret scanning for non-Python files + safe YAML loader checks + SSRF detection |
| `diff_engine.py` | `DiffAwareScanner` | Parses unified diffs; tags findings as `is_new: True/False` based on changed lines |
| `context_validator.py` | `ContextValidator` | Reduces false positives (placeholders, test files, comments, env-var sources) |
| `test_file_fetcher.py` | — | Predicts/fetches test files + dependencies (GitHub raw/code commits, commit-validated) |

**Vulnerability Types Detected**:
| Type | Detection | Severity |
|------|-----------|----------|
| COMMAND_INJECTION | `os.system()` / `subprocess(shell=True)` | HIGH |
| CODE_INJECTION | `eval()` / `exec()` calls | HIGH |
| HARDCODED_SECRET | Assignments to secret-named variables (regex + AST) | HIGH |
| INSECURE_DESERIALIZATION | `pickle.loads()` / `marshal` / `shelve` | HIGH |
| SQL_INJECTION | Dynamic strings in `execute()` / `executemany()` | HIGH |
| PATH_TRAVERSAL | Unsanitized dynamic paths in `open()` | HIGH |
| SSRF | Dynamic URLs in `requests.*` / `urllib` / `httpx` | HIGH |
| WEAK_CRYPTOGRAPHY | `hashlib.md5` / `sha1` / `new("md5")` | MEDIUM |
| TLS_VERIFICATION_DISABLED | `requests(verify=False)` | LOW (silent) |
| DEBUG_CODE | `breakpoint()` / `pdb` | LOW (silent) |

**Data Flow**:
```
File → VulnerabilityScanner.scan_file()
    → AST Parse
    → NodeVisitor visits nodes → matches 10 vulnerability patterns
    → Regex secret scanning (for .env, .yaml, .json, .toml files)
    → DiffAwareScanner filters to changed lines (is_new)
    → ContextValidator validates findings (filters placeholders)
    → Returns: List[vulnerability] (Pydantic dict)
```

---

### 3. **Patching Layer** (`core/patch/`)

**Purpose**: Generate and apply secure patches via AST transformations and LLM innovation

| Module | Component | Role |
|--------|-----------|------|
| `fixers.py` | `BaseTransformer` / `apply_patch_to_content` | AST patch engine; fuzzy matching via `ast.get_source_segment`; `SUPPORTED_FIXER_TYPES` (all types except TLS/DEBUG/CIPHER) |
| `patch_orchestrator.py` | `apply_patches_safely()` | Conflict-safe orchestration; sorts patches by line descending, tracks `used_lines`, skips conflicts |
| `llm_patcher.py` | `LLMPatcher` | Gemini multi-candidate generation; quality-ordered fallback chain; retry/backoff; rate-limit semaphore; SHA256 prompt caching |

**Patch Types Supported**:
- **COMMAND_INJECTION**: `subprocess.run(shlex.split(cmd), shell=False)`
- **CODE_INJECTION**: `ast.literal_eval(data)` instead of `eval()`
- **HARDCODED_SECRET**: Move to `os.getenv('KEY')`
- **INSECURE_DESERIALIZATION**: Use `json.loads()` instead of `pickle.loads()`
- **SQL_INJECTION**: Parameterized queries using tuple binds
- **PATH_TRAVERSAL**: Sanitize dynamic path components via `os.path.basename()` / `safe_path_join()`
- **SSRF**: Wrap URLs with `validate_url_ssrf()` (scheme/domain validation helper)
- **WEAK_CRYPTOGRAPHY**: Replace MD5/SHA1 with `hashlib.sha256()`

**LLM Innovation**:
- Gemini fallback chain: `gemini-3.5-flash` → `gemini-3.6-flash` → `gemini-3.5-flash-lite` → `gemini-3.1-flash-lite`
- Candidates validated alongside AST baseline; best-ranked candidate wins
- Prompt caching by SHA-256; safe candidate generation with `PatchCache`

---

### 4. **Validation Layer** (`core/validator/`)

**Purpose**: Ensure patches are safe, effective, and policy-compliant

| Module | Class | Role |
|--------|-------|------|
| `patch_validator.py` | `PatchValidator` | Syntax check (`ast.parse`) + imports (`DANGEROUS_IMPORTS`: socket/ctypes) + policy + SSRF validation |
| `sandbox.py` | `Sandbox` | Docker-based safe execution with limits; `BLOCKED_PATTERNS`; local fallback with `setrlimit`; `SandboxCache` |
| `security_rescan.py` | `SecurityRescanner` | Re-scans patched code; `success=False` if still vulnerable |
| `test_rebind.py` | `rebind_test_imports()` | Rewrites `tests/` package imports to the module under validation before pytest |

**Validation Chain**:
```
Patched Code
    → STAGE 1: Syntax & Semantic Checks (ast.parse + imports + SSRF)
    → STAGE 2: Sandbox Execution
        → Docker: read-only fs, network none, cap-drop ALL, CPU 0.5, mem 512m,
          pids 32, tmpfs 64m, no-new-privileges, timeouts (10s / 60s tests)
        → Local fallback: setrlimit (Linux) + strip_secrets + timeouts
    → STAGE 3: Test execution (rebind imports → pytest) 
    → STAGE 4: Security Re-scan (SecurityRescanner)
    → STAGE 5: Policy Compliance (PolicyEngine)
```

---

### 5. **Policy Engine** (`core/policy/`)

**Purpose**: Enforce organizational security standards

| Module | Component | Role |
|--------|-----------|------|
| `policy_engine.py` | `PolicyEngine` | Loads Pydantic `config.policy` from YAML; `check_compliance`, `enforce_sanitizers`, `apply_policy` |
| `config/policy/default.yaml` | Configuration | Forbidden modules/functions, mandatory sanitizers, sensitive paths, wrappers, query params |

**Policy Checks**:
- **Forbidden Modules**: `marshal`, `shelve`, `telnetlib`
- **Forbidden Functions**: `os.system`, `os.popen`, `eval`, `exec`, `hashlib.md5`, `hashlib.sha1`
- **Mandatory Sanitizers**: `subprocess.run/Popen(..., shell=False)`
- **Sensitive Paths**: `auth/`, `secrets/`, `credentials/`, `billing/`
- **Restricted Args**: `hashlib.new("md5"/"sha1"/"md4"/"sha")` blocked
- **Mandatory Wrappers**: `validate_url_ssrf()` for `requests.*`/`urllib.request.urlopen`/`httpx.*`; `os.path.basename`/`safe_path_join` for `open()`
- **Forbidden Assignments**: `*password*`, `*secret*`, `*token*`, `*api_key*`, `*apikey*`, `*private_key*`
- **Parameterized Queries**: `execute`/`executemany` must use tuple params (not f-string/%)

---

### 6. **Risk Analysis Layer** (`core/risk/`)

**Purpose**: Compute risk scores and explain findings

| Module | Function/Class | Role |
|--------|---------------|------|
| `risk_engine.py` | `compute_risk`, `explain_risk` | Weighted risk scoring (8 factors) + breakdown explanation |
| `context_engine.py` | `ContextRiskEngine` | Context-aware adjustments |
| `metrics_extractor.py` | `extract_metrics()` | Code complexity metrics (cyclomatic, nesting, LOC) |

**Risk Scoring** (weights from `config/risk.yaml`):
```
Risk = Σ(weight_i × normalize_i(factor_i))

Weights:
  - Severity:        0.22
  - Vulnerability Type: 0.14
  - Validation:      0.16
  - Confidence:      0.12
  - Complexity:      0.00 (negative reward in quality layer)
  - Sensitivity:     0.12
  - Exposure:        0.12
  - Quality:         0.12

Gating (config/risk.yaml):
  - auto_request_changes_above: 4.0  → REQUEST_CHANGES
  - max_allowed_risk:           8.5  → REQUEST_CHANGES (critical)
```

**Patch Quality Scoring** (`core/quality/patch_scorer.py`): 6 weighted factors — syntax validity (0.20), security validation (0.25), tests passed (0.20), complexity (negative, reward for low), formatting preserved (0.10), confidence (0.15).

---

### 7. **Confidence Layer** (`core/confidence/`)

**Purpose**: Assess patch reliability and learn from historical outcomes

| Module | Component | Role |
|--------|-----------|------|
| `confidence.py` | `calculate_confidence()` | Per-type `BASE_CONFIDENCE`; adjusted by validation, severity, tests (docker/local), quality, patch length |
| `learning_engine.py` | `ConfidenceLearningEngine` | Time-weighted decay (30-day half-life), min sample size, ACCEPTED-rate adjustments |

**Confidence Inputs**:
- Patch type (known/unknown base confidence)
- Validation results (syntax, sandbox, re-scan, policy)
- Test execution mode (docker +0.12 / local +0.06 / other +0.04)
- Historical success rate (learning engine: ≥90% → +0.10 … ≤25% → −0.15)
- Code complexity + patch length

---

### 8. **GitHub Integration** (`services/github/`)

**Purpose**: Authenticate with GitHub, fetch PR files, post reports, collect feedback

| Module | Function | Role |
|--------|----------|------|
| `auth.py` | `generate_jwt()`, `get_installation_token()` | GitHub App JWT (exp 540s, raw PEM or path) + installation access tokens; OAuth session + refresh |
| `reporter.py` | `format_report()`, `post_pr_comment()`, `update_pr_comment()`, `set_pr_labels()`, `generate_sarif()`, `upload_sarif_to_code_scanning()` | Hybrid report (New vs Legacy), bot-comment dedup/update, risk labels, SARIF upload + polling + alert reconciliation |

**Auto-Feedback Mechanisms**:
- **🚀 Reactions**: 🚀/👍 recorded as ACCEPTED, 👎/-1 as REJECTED via webhook reaction events
- **PR Merges**: merged PRs auto-resolve and record ACCEPTED
- **SARIF Dismissals**: reconciled with Code Scanning alerts (`check_all_alerts_dismissed`)

---

### 9. **Data & Config Layers**

| Module | Purpose |
|--------|--------|
| `core/config/` | Pydantic v2 models (AppConfig, RiskConfig, PolicyConfig, QualityConfig, SandboxConfig); `ConfigRegistry` lazy-loads `config/*.yaml` |
| `core/models/` | Pydantic v2 models: `Vulnerability`, `VulnerabilityType` (10), `Severity`, `ScanResult`, `PatchCandidate/Result`, `RiskAssessment`, validation results |
| `core/metadata/vuln_metadata.py` | Rule IDs, vuln names, CVSS-like severities, CWE/OWASP mappings |
| `core/sarif/` | SARIF 2.1.0 generator (converter + generator) |
| `core/cache/` | SQLite-backed caches: `scan_cache`, `gemini_cache`, `test_file_cache`, `ast_cache` (safe RestrictedUnpickler); in-proc `sandbox_cache` |
| `core/llm/` | Gemini client + `model_resolver` fallback chain |
| `core/exceptions/` | Typed exceptions under `AIRiskGuardError` |
| `core/utils/` | `tempdir`, `validation` (safe paths, diff size, extensions) |
| `utils/logger.py` | Structured JSON logging to `data/logs.json` + stdout |
| `utils/db.py` | SQLite persistence: users, repos, scans, findings, pr_findings, patch_feedback, caches, dashboard |
| `utils/retry.py` | Retry with backoff for transient failures |

---

## Entry Points

### 1. **CLI** (`app/main.py`)
```python
if __name__ == "__main__":
    engine = AIRiskGuard()
    findings = engine.analyze_file("path/to/file.py")
    print(format_report(findings))
```

### 2. **Webhook Server** (`app/app.py`)
- Serves via **waitress** on `0.0.0.0:8000` (or `PORT` env)
- Handles webhook events: `pull_request` (opened/synchronize/reopened), `installation`, `installation_repositories`, `reaction`, `pull_request` closed/merged
- HMAC-SHA256 verification, 300s dedup, ThreadPoolExecutor (max 3)
- OAuth login/refresh, repo sync from installations
- Serves SPA at `/` and `/dashboard`; 30+ `/api/*` routes; Prometheus at `/api/metrics/prometheus`

---

## Data Models

### Vulnerability (Pydantic v2 — `core/models/vulnerability.py`)
```python
class VulnerabilityType(Enum):
    COMMAND_INJECTION, CODE_INJECTION, HARDCODED_SECRET,
    INSECURE_DESERIALIZATION, SQL_INJECTION, PATH_TRAVERSAL,
    SSRF, WEAK_CRYPTOGRAPHY, TLS_VERIFICATION_DISABLED, DEBUG_CODE

class Severity(Enum): HIGH | MEDIUM | LOW

class Vulnerability(BaseModel):
    type: VulnerabilityType
    file: str
    line: int
    code: str
    severity: Severity
    message: str
    description: str | None
    cwe: str | None            # e.g. CWE-78
    owasp: str | None          # e.g. A03:2021 – Injection
    is_new: bool               # from diff-aware scanning
    function: str | None
    context_lines: list | None
```

### Scan Result
```python
class ScanResult(BaseModel):
    success: bool
    vulnerabilities: list[Vulnerability]
    # + ISO-8601 timestamps
```
Analysis results also include patch candidates, validation stages (syntax/sandbox/rescan/policy), confidence, and 8-factor risk with breakdown.

---

## Execution Flow (Webhook)

```
1. GitHub sends POST /webhook (opened/synchronize/reopened, installation, reaction, closed)
2. verify signature (X-Hub-Signature-256) + dedup (300s TTL)
3. Extract repo_name, PR number, installation_id; upsert repo from payload
4. Submit to ThreadPoolExecutor (background, returns 202 immediately)
5. Background worker (zero-copy, no disk clone):
   a. Fetch PR files via GitHub API (paginated, up to 1000+)
   b. For each modified target file:
      i.   Fetch full content via GitHub API
      ii.  Write to TempDir
      iii. ManagerAgent.process_file():
           ├─ ScannerAgent.execute() → vulnerabilities + test discovery
           ├─ PatchAgent.execute() → AST baseline + Gemini candidates
           ├─ ValidatorAgent.execute() → per-candidate validation + tests
           ├─ RiskAgent.execute() → quality, risk, confidence, evidence
           └─ OrchestrationAgent.execute() → decision, labels, SARIF
   c. Post PR comment (parallel with SARIF upload)
   d. Persist scan/findings/feedback/dashboard metrics
6. Return 202 Accepted (immediate)
```

---

## Dependencies

### External Packages (by category)
- **Web**: flask, waitress
- **GitHub**: PyJWT, requests
- **Security**: cryptography, bcrypt
- **Data**: pydantic v2, numpy
- **Config**: PyYAML
- **DevOps**: docker (via API)
- **LLM**: google-genai (Gemini 2.5/1.5/2.0 Flash)
- **Ops**: prometheus_client, psutil
- **Testing**: pytest, hypothesis, pytest-mock, pytest-cov
- **Utilities**: python-dotenv, python-dateutil, httpx, aiohttp

### Internal Dependency Graph
```
app/app.py (Flask: webhook, OAuth, API, SPA)
    ├─ core/config (ConfigRegistry → Pydantic models)
    ├─ core/models (Pydantic v2)
    ├─ app/main.py (AIRiskGuard → ManagerAgent)
    │  ├─ core/agents/manager_agent.py
    │  │  ├─ core/agents/scanner_agent.py
    │  │  │  ├─ core/scanner/vulnerability_scanner.py
    │  │  │  │  ├─ core/scanner/diff_engine.py
    │  │  │  │  ├─ core/scanner/context_validator.py
    │  │  │  │  └─ core/metadata/vuln_metadata.py
    │  │  │  └─ core/scanner/test_file_fetcher.py
    │  │  ├─ core/agents/patch_agent.py
    │  │  │  ├─ core/patch/patch_orchestrator.py
    │  │  │  ├─ core/patch/fixers.py
    │  │  │  └─ core/patch/llm_patcher.py (core/llm + core/cache)
    │  │  ├─ core/agents/validator_agent.py
    │  │  │  ├─ core/validator/patch_validator.py
    │  │  │  ├─ core/validator/sandbox.py
    │  │  │  ├─ core/validator/security_rescan.py
    │  │  │  ├─ core/validator/test_rebind.py
    │  │  │  └─ core/policy/policy_engine.py
    │  │  ├─ core/agents/risk_agent.py
    │  │  │  ├─ core/quality/patch_scorer.py
    │  │  │  ├─ core/risk/risk_engine.py
    │  │  │  ├─ core/confidence/confidence.py + learning_engine.py
    │  │  │  └─ core/policy/policy_engine.py
    │  │  └─ core/agents/orchestrator_agent.py
    │  │     └─ core/sarif + services/github/reporter.py
    │  └─ services/github/reporter.py (auth, sarif)
    ├─ utils/db.py, utils/logger.py, utils/retry.py
    └─ app/metrics.py (Prometheus)
```

---

## Known Issues & Gaps

1. **Local fallback isolation**: without Docker, code executes with `setrlimit` (Linux) + strip-secrets + timeouts — reduced isolation vs Docker.
2. **SQLite single-node**: concurrent write scaling may need Postgres/Redis.
3. **`GEMINI_API_KEY` optional**: LLM patching disabled, AST-only fallback.
4. **LLM determinism**: Gemini candidates are non-deterministic; quality scoring ranks best-effort.
5. **Windows local fallback**: `resource.setrlimit` unavailable → timeout + strip_secrets only.

---

## Configuration

- YAML configs loaded by `ConfigRegistry` (`core/config`): `app.yaml`, `risk.yaml`, `policy/default.yaml`, `quality.yaml`, `sandbox.yaml`
- **Env vars**: `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY` (PEM content or path), `GITHUB_WEBHOOK_SECRET`, `GITHUB_APP_CLIENT_ID`, `GITHUB_APP_CLIENT_SECRET`, `GEMINI_API_KEY`, `FLASK_SECRET_KEY`, `SESSION_COOKIE_SECURE`, `FRONTEND_ORIGIN`, `PORT`, `DB_PATH`

---

## Dashboard

A React 18 + Vite SPA (built into `../static/frontend`) served by Flask at `/`:
- **Stack**: React, Vite, Tailwind CSS, Chart.js, react-chartjs-2, framer-motion, axios
- **Design system**: custom CSS-variable tokens with three-pillar zones — **Blue** (tech/primary), **Red** (energy/critical), **Silver** (data/structure)
- **Pages**: Landing, Dashboard, Repositories, RepositoryDetail, Scans, ScanDetail, FindingsExplorer, Metrics, Pipeline, Policy, Settings, Status, Docs, Login
- **Features**: OAuth-gated pages, 30s live refresh, light/dark themes, risk charts, findings triage with Resolve/Dismiss/Reopen, patch feedback, policy viewer, settings (scan_mode, sandbox_network)
- **Database**: SQLite (`data/dashboard.db`) — scans, findings, feedback, dashboard stats, caches
