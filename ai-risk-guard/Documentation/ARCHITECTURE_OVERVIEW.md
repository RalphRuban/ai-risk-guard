# AI Risk Guard - Architecture Overview

## Project Summary
**AI Risk Guard** is a GitHub-integrated security vulnerability scanner and patch generator for Python code. It detects security issues (command injection, code injection, hardcoded secrets, insecure deserialization), applies AST-based patches, validates the fixes, and reports findings to GitHub PRs.

**Tech Stack**: Python 3.x | FastAPI/Flask | GitHub App | SQLite | AST/Regex Analysis | ML (scikit-learn, SHAP)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub (via Webhook)                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Flask Webhook Handler                          │
│                      (app/app.py)                                │
│  • Verifies GitHub webhook signature                             │
│  • Clones PR repository                                          │
│  • Orchestrates analysis pipeline                                │
│  • Posts PR comments with findings                               │
└───────────┬───────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Main Risk Guard Engine (app/main.py)                │
│                    class AIRiskGuard                             │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  1. SCANNING PHASE                                       │   │
│  │     └─ VulnerabilityScanner (core/scanner/)              │   │
│  │        ├─ AST Analysis (ASTScanner)                      │   │
│  │        ├─ Regex Patterns (RegexScanner)                  │   │
│  │        ├─ Diff Awareness (DiffAwareScanner)              │   │
│  │        ├─ Entropy Detection (EntropyDetector)            │   │
│  │        └─ Context Validation (ContextValidator)          │   │
│  │                                                            │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │  2. PATCHING PHASE                                       │   │
│  │     └─ Patch Orchestrator (core/patch/)                  │   │
│  │        ├─ Safe Patch Application                         │   │
│  │        ├─ Conflict Analysis                              │   │
│  │        └─ AST-based Fixes (fixers.py)                    │   │
│  │                                                            │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │  3. VALIDATION PHASE                                     │   │
│  │     ├─ PatchValidator (syntax/semantic checks)           │   │
│  │     ├─ Sandbox (safe code execution)                     │   │
│  │     └─ SecurityRescanner (rescan patched code)           │   │
│  │                                                            │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │  4. ANALYSIS PHASE                                       │   │
│  │     ├─ Risk Scoring (core/risk/)                         │   │
│  │     │  ├─ Severity normalization                         │   │
│  │     │  ├─ Type weighting                                 │   │
│  │     │  ├─ Validation impact                              │   │
│  │     │  └─ Context-aware risk engine                      │   │
│  │     │                                                     │   │
│  │     ├─ Confidence Scoring (core/confidence/)             │   │
│  │     │  └─ Learning engine for historical accuracy        │   │
│  │     │                                                     │   │
│  │     └─ Metrics Extraction (code complexity)              │   │
│  │                                                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│              GitHub PR Reporting (services/github/)              │
│  • Format report with findings                                   │
│  • Post comments to PR                                           │
│  • GitHub App auth (JWT + Installation tokens)                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. **Scanning Layer** (`core/scanner/`)

**Purpose**: Detect vulnerabilities using multiple scanning strategies

| Module | Class/Function | Role |
|--------|---|---|
| `vulnerability_scanner.py` | `VulnerabilityScanner` | Main orchestrator; combines AST, regex, and diff scanning |
| `ast_scanner.py` | `ASTScanner(NodeVisitor)` | Detects unsafe patterns: `os.system()`, `eval()`, `pickle.loads()`, subprocess commands |
| `regex_scanner.py` | `RegexScanner` | Pattern-based detection: hardcoded secrets, API keys via regex |
| `diff_engine.py` | `DiffAwareScanner` | Analyzes code diffs; only flags vulnerabilities in changed lines |
| `context_validator.py` | `ContextValidator` | Reduces false positives; validates if input is truly user-controlled |
| `entropy_detector.py` | `EntropyDetector` | Shannon entropy analysis for detecting random tokens (potential secrets) |

**Data Flow**:
```
File → VulnerabilityScanner.scan_file()
    → AST Parse
    → ASTScanner visits nodes → matches patterns
    → RegexScanner applies patterns
    → DiffAwareScanner filters to changed lines only
    → ContextValidator validates findings
    → Returns: List[vulnerability_dict]
```

---

### 2. **Patching Layer** (`core/patch/`)

**Purpose**: Generate and apply safe patches to vulnerable code

| Module | Key Component | Role |
|--------|---|---|
| `patch_orchestrator.py` | `apply_patches_safely()` | Transaction-safe orchestration; sorts patches, detects conflicts |
| `fixers.py` | `apply_patch_to_content()` | Main patch engine; AST transformations for each vuln type |
| `ast_patch_engine.py` | `apply_patch_to_content()` | **[DEPRECATED]** Duplicate of fixers.py; not used in main flow |
| `conflict_analyzer.py` | `ConflictAnalyzer` | Simple conflict detection (basic line-collision tracking) |
| `patch_generator.py` | `generate_patch()` | Creates illustrative patch snippets for PR comments |
| `dependency_graph.py` | `DependencyGraph` | Topological patch ordering; **unused** |
| `transformers.py` | `BaseTransformer` | **[UNUSED]** Base class for AST transforms; duplicate of fixers.py |

**Patch Types Supported**:
- **COMMAND_INJECTION**: `subprocess.run(shlex.split(cmd), shell=False)`
- **CODE_INJECTION**: `ast.literal_eval(data)` instead of `eval()`
- **HARDCODED_SECRET**: Move to `os.getenv('KEY')`
- **INSECURE_DESERIALIZATION**: Use `json.loads()` instead of `pickle.loads()`

---

### 3. **Validation Layer** (`core/validator/`)

**Purpose**: Ensure patches are safe and effective

| Module | Class | Role |
|--------|---|---|
| `patch_validator.py` | `PatchValidator` | Validates syntax, checks for unsafe patterns in patched code |
| `sandbox.py` | `Sandbox` | Safely executes patched code; detects runtime errors |
| `security_rescan.py` | `SecurityRescanner` | **[BUG]** Re-scans patched code; has critical initialization error |

**Validation Chain**:
```
Patched Code
    → PatchValidator.validate_all()
        → Syntax check (ast.parse)
        → Semantic checks (unsafe pattern detection)
    → Sandbox.run()
        → Execute with timeout
        → Catch exceptions
    → SecurityRescanner.rescan_code()
        → Scan patched code for remaining vulnerabilities
```

---

### 4. **Risk Analysis Layer** (`core/risk/`)

**Purpose**: Compute risk scores and explain findings

| Module | Function/Class | Role |
|--------|---|---|
| `risk_engine.py` | `calculate_risk()` | Weighted risk scoring (7 factors) |
| `context_engine.py` | `ContextRiskEngine` | Context-aware adjustments (file type, PR owner, etc.) |
| `metrics_extractor.py` | `extract_metrics()` | Code complexity metrics (cyclomatic, nesting, LOC) |

**Risk Scoring Formula**:
```
Risk = Σ(weight_i × normalize_i(factor_i))

Weights:
  - Severity: 0.22
  - Vulnerability Type: 0.14
  - Validation Status: 0.18
  - Patch Confidence: 0.12
  - Code Complexity: 0.10
  - Sensitivity (file type): 0.12
  - Exposure (PR visibility): 0.12
```

---

### 5. **Confidence Layer** (`core/confidence/`)

**Purpose**: Assess patch reliability

| Module | Component | Role |
|--------|---|---|
| `confidence.py` | `calculate_confidence()` | Scores how confident we are in the patch |
| `learning_engine.py` | `ConfidenceLearningEngine` | Tracks historical accuracy; learns from past patches |

**Confidence Inputs**:
- Patch type (known/unknown)
- Validation results
- Historical success rate
- Code complexity

---

### 6. **GitHub Integration** (`services/github/`)

**Purpose**: Authenticate with GitHub, fetch PRs, post reports

| Module | Function | Role |
|--------|---|---|
| `auth.py` | `generate_jwt()`, `get_installation_token()` | GitHub App authentication |
| `reporter.py` | `post_pr_comment()`, `format_report()` | Formats findings, posts to PR |
| `pr_fetcher.py` | `fetch_pr_files()` | **[UNUSED]** Fetches PR file data (not used; clone via git instead) |

---

### 7. **Utilities**

| Module | Purpose |
|--------|---|
| `utils/logger.py` | Structured JSON logging to `data/logs.json` + stdout |
| `utils/db.py` | SQLite persistence for dashboard counters |
| `core/metadata/vuln_metadata.py` | Vulnerability type metadata (CWE, OWASP, severity) |
| `core/reporting/explainer.py` | Generates human-readable explanations |

---

## Entry Points

### 1. **Main CLI** (`app/main.py`)
```python
if __name__ == "__main__":
    engine = AIRiskGuard()
    findings = engine.analyze_file("path/to/file.py")
    print(format_report(findings))
```
**Usage**: `python app/main.py myfile.py`

### 2. **GitHub Webhook Server** (`app/app.py`)
- Runs Flask on `0.0.0.0:8000`
- Listens for `pull_request` events
- Verifies HMAC-SHA256 webhook signature
- Clones repo, scans files, posts results

---

## Data Models

### Vulnerability Dictionary
```python
vulnerability = {
    "type": "COMMAND_INJECTION",          # One of 4 known types
    "file": "src/app.py",
    "line": 42,
    "column": 10,
    "severity": "HIGH",                    # From VULN_METADATA
    "description": "Unsafe shell execution",
    "context": "os.system(user_input)",    # Code snippet
}
```

### Analysis Result
```python
result = {
    "vulnerability": {...},                 # See above
    "patch": "patched code string",
    "diff": "unified diff",
    "validation": {"success": bool, ...},
    "sandbox": {"success": bool, ...},
    "rescan": {"success": bool, ...},
    "confidence": 0.85,
    "risk": 7.2,
    "risk_breakdown": {"severity": ..., "type": ...},
}
```

---

## Execution Flow (Webhook)

```
1. GitHub sends POST /webhook with PR event
2. verify_signature() validates HMAC-SHA256
3. Extract repo URL, PR number, installation ID
4. generate_jwt() + get_installation_token()
5. Clone repo to temp directory
6. For each .py file:
    a. AIRiskGuard.analyze_file()
       ├─ scanner.scan_file() → [vulnerabilities]
       ├─ apply_patches_safely() → patched_code
       ├─ validator.validate_all()
       ├─ sandbox.run()
       ├─ rescanner.rescan_code()
       ├─ calculate_confidence()
       ├─ calculate_risk()
       └─ → [results]
7. format_report(results) → markdown
8. post_pr_comment(report) → GitHub
9. Return 200 OK
```

---

## Dependencies

### External Packages (by category)
- **Web**: fastapi, uvicorn, flask, starlette
- **GitHub**: PyGithub, PyJWT, requests
- **Security**: cryptography, PyNaCl
- **Data**: pandas, numpy, SQLAlchemy
- **ML/Analysis**: scikit-learn, xgboost, shap, numba
- **DevOps**: docker, gitpython
- **Utilities**: python-dotenv, tqdm, click

### Internal Dependency Graph
```
app/app.py
    ├─ app/main.py (AIRiskGuard)
    │  ├─ core/scanner/vulnerability_scanner.py
    │  ├─ core/patch/patch_orchestrator.py
    │  ├─ core/patch/fixers.py
    │  ├─ core/validator/patch_validator.py
    │  ├─ core/validator/sandbox.py
    │  ├─ core/validator/security_rescan.py
    │  ├─ core/confidence/confidence.py
    │  ├─ core/risk/risk_engine.py
    │  └─ services/github/reporter.py
    ├─ services/github/auth.py
    └─ utils/logger.py

services/github/reporter.py
    ├─ core/reporting/explainer.py
    └─ core/metadata/vuln_metadata.py
```

---

## Known Issues & Gaps

1. **Critical Bug**: `security_rescan.py` has undefined `scan_file` reference (line 6)
2. **Dead Code**: `ast_patch_engine.py` duplicates `fixers.py` but not used
3. **Unused**: `dependency_graph.py`, `transformers.py`, `pr_fetcher.py`
4. **Incomplete**: `ConflictAnalyzer` registers patches but tracking incomplete
5. **Not Integrated**: `patch_generator()` creates snippets but never called

---

## Configuration

- **GitHub App ID**: `GITHUB_APP_ID` env var
- **Private Key**: `GITHUB_PRIVATE_KEY` env var (PEM format)
- **Webhook Secret**: `GITHUB_WEBHOOK_SECRET` env var
- **DB Path**: `DB_PATH` env var (default: `data/dashboard.db`)
- **Debug Mode**: Flask `debug=True` in `app.py`
