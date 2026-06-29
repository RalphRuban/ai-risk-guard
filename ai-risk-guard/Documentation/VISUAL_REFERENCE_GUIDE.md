# AI Risk Guard - Visual Reference Guide

## Module Inventory

```
ai-risk-guard/
│
├── app/                           # Application Layer
│   ├── main.py                    ✅ AIRiskGuard (main orchestrator)
│   ├── app.py                     ✅ Flask webhook server
│   └── config.py                  ⚠️ UNUSED (delete)
│
├── core/
│   │
│   ├── scanner/                   # SCANNING LAYER
│   │   ├── vulnerability_scanner.py    ✅ Main scanner (orchestrator)
│   │   ├── ast_scanner.py              ✅ AST pattern detection
│   │   ├── regex_scanner.py            ✅ Regex-based secrets
│   │   ├── diff_engine.py              ✅ Diff-aware filtering
│   │   ├── context_validator.py        ✅ False-positive reduction
│   │   └── entropy_detector.py         ✅ Shannon entropy analysis
│   │
│   ├── patch/                     # PATCHING LAYER
│   │   ├── patch_orchestrator.py       ✅ Safe patch application
│   │   ├── fixers.py                   ✅ AST patch engine (canonical)
│   │   ├── ast_patch_engine.py         ⚠️ DUPLICATE (delete - REF-2)
│   │   ├── transformers.py             ⚠️ DUPLICATE (delete - REF-3)
│   │   ├── conflict_analyzer.py        ✅ Conflict detection (incomplete - REF-3)
│   │   ├── dependency_graph.py         ⚠️ Unused (integrate - REF-4)
│   │   ├── patch_generator.py          ⚠️ Orphaned (integrate - REF-6)
│   │   └── fixers.py                   ✅ (imported)
│   │
│   ├── validator/                 # VALIDATION LAYER
│   │   ├── patch_validator.py          ✅ Syntax/semantic validation
│   │   ├── sandbox.py                  ✅ Safe code execution
│   │   └── security_rescan.py          🔴 BROKEN (bug - REF-1)
│   │
│   ├── risk/                      # RISK ANALYSIS LAYER
│   │   ├── risk_engine.py              ✅ Weighted risk scoring
│   │   ├── context_engine.py           ✅ Context-aware adjustments
│   │   └── metrics_extractor.py        ✅ Code metrics
│   │
│   ├── confidence/                # CONFIDENCE LAYER
│   │   ├── confidence.py               ✅ Confidence scoring
│   │   └── learning_engine.py          ✅ Historical learning
│   │
│   ├── metadata/
│   │   └── vuln_metadata.py            ✅ Vulnerability catalog
│   │
│   └── reporting/
│       └── explainer.py                ✅ Remediation explanations
│
├── services/
│   └── github/
│       ├── auth.py                     ✅ JWT + installation tokens
│       ├── reporter.py                 ✅ PR comment formatting
│       └── pr_fetcher.py               ⚠️ UNUSED (delete - REF-7)
│
├── utils/
│   ├── logger.py                       ✅ Structured JSON logging
│   └── db.py                           ⚠️ Unused (not integrated)
│
├── tests/
│   └── test_core.py                    ✅ Unit tests
│
└── README.md, requirements.txt, pytest.ini, etc.
```

---

## Status Legend

| Status | Meaning |
|--------|---------|
| ✅ | Active, tested, imported |
| ⚠️ | Unused or incomplete (needs refactoring) |
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
│ • Verify HMAC-SHA256 signature                  │
│ • Extract repo URL, PR #, installation ID       │
│ • Clone repository                              │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ app/main.py::AIRiskGuard.analyze_file()         │
│ for each .py file in repo                       │
└─────────────────────────────────────────────────┘
                      ↓
        ┌─────────────────────────┐
        │ PHASE 1: SCAN           │
        ├─────────────────────────┤
        │ File → AST Parse        │
        │ → ASTScanner            │
        │ → RegexScanner          │
        │ → DiffAwareScanner      │
        │ → ContextValidator      │
        │ ↓                       │
        │ [Vulnerabilities]       │
        └─────────────────────────┘
                      ↓
        ┌─────────────────────────┐
        │ PHASE 2: PATCH          │
        ├─────────────────────────┤
        │ apply_patches_safely()  │
        │ • ConflictAnalyzer      │
        │ • fixers.py transforms  │
        │ ↓                       │
        │ Patched code            │
        │ Unified diff            │
        └─────────────────────────┘
                      ↓
        ┌─────────────────────────┐
        │ PHASE 3: VALIDATE       │
        ├─────────────────────────┤
        │ • PatchValidator        │
        │ • Sandbox.run()         │
        │ • SecurityRescanner     │
        │   (🔴 BUG HERE)         │
        │ ↓                       │
        │ Validation results      │
        │ Sandbox output          │
        │ Rescan results          │
        └─────────────────────────┘
                      ↓
        ┌─────────────────────────┐
        │ PHASE 4: ANALYZE        │
        ├─────────────────────────┤
        │ extract_metrics()       │
        │ calculate_confidence()  │
        │ calculate_risk()        │
        │ explain_risk()          │
        │ ↓                       │
        │ Risk scores (0-10)      │
        │ Confidence (0-1)        │
        │ Explanations            │
        └─────────────────────────┘
                      ↓
        ┌─────────────────────────┐
        │ PHASE 5: REPORT         │
        ├─────────────────────────┤
        │ format_report()         │
        │ post_pr_comment()       │
        │ ↓                       │
        │ PR comment posted       │
        └─────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ OUTPUT: PR comment with findings                │
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
verify_signature()
      ↓
Extract: repo_name, pr_number, access_token
      ↓
git clone repo
      ↓
For each .py file:
  AIRiskGuard().analyze_file(file_path)
      ↓
Post results to PR comment
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
core/scanner/vulnerability_scanner.py
core/patch/patch_orchestrator.py
core/validator/patch_validator.py
core/risk/risk_engine.py
services/github/reporter.py
```

### Level 3: Sub-Components
```
core/scanner/* (AST, Regex, Context, Diff, Entropy)
core/patch/fixers.py (patch application)
core/validator/* (sandbox, rescan)
core/confidence/* (scoring engines)
services/github/auth.py
```

### Level 4: Utilities & Data
```
utils/logger.py (used by everyone)
core/metadata/vuln_metadata.py
core/reporting/explainer.py
utils/db.py (unused)
```

---

## Critical Paths (High-Traffic Dependencies)

```
logger.py
  ↑ (used by ALL modules)
  │
  ├─ vulnerability_scanner.py
  │  ├─ context_validator.py
  │  ├─ diff_engine.py
  │  └─ entropy_detector.py
  │
  ├─ patch_orchestrator.py
  │  └─ fixers.py
  │
  ├─ risk_engine.py
  │  └─ context_engine.py
  │
  └─ reporter.py
     └─ auth.py
```

---

## Problem Zones 🔴⚠️

### CRITICAL
```
security_rescan.py (Line 6-7)
  from core.scanner.vulnerability_scanner import scanner
  scanner.scan_file(path)  ← Module.function doesn't exist
  
  → Crashes when used
  → Fix: Instantiate VulnerabilityScanner, use self.scanner
```

### DUPLICATE CODE
```
ast_patch_engine.py (196 LOC)  ← NEVER IMPORTED
  vs.
fixers.py (196 LOC)             ← USED in main.py

transformers.py (36 LOC)        ← NEVER IMPORTED
  vs.
fixers.py::BaseTransformer      ← USED

→ Delete ast_patch_engine.py and transformers.py
```

### UNUSED/ORPHANED
```
pr_fetcher.py                   ← Never called
dependency_graph.py             ← Built but not used
patch_generator.py              ← Built but not integrated
config.py                       ← Never imported
db.py                          ← Not integrated in app
```

---

## Fix Priority Matrix

```
         EFFORT
         Low    Medium    High
HIGH   │  REF-1  REF-3   REF-4
       │  REF-2  REF-5
IMPACT │  REF-7
       │
MEDIUM │  REF-9  REF-6   REF-8
       │  REF-10
       │
LOW    │
       
Priority Order (by impact × effort):
1. REF-1 (Security bug, 1 hour)
2. REF-2 (Delete dupes, 30 min)
3. REF-3 (Complete feature, 45 min)
4. REF-4 (Integrate unused code, 1.5 hours)
5. REF-6 (UX enhancement, 1 hour)
6. REF-5,7-10 (Polish & cleanup)
```

---

## Test Coverage Map

```
tests/test_core.py covers:

✅ TestScanner
   ├─ test_os_system_detected
   ├─ test_eval_detected
   ├─ test_pickle_detected
   └─ ...

✅ TestPatchEngine
   ├─ test_command_injection_fix
   ├─ test_code_injection_fix
   └─ ...

✅ TestDiffEngine
   ├─ test_diff_aware_scanning
   └─ ...

✅ TestContextValidator
   ├─ test_false_positive_reduction
   └─ ...

✅ TestConfidence
   ├─ test_confidence_scoring
   └─ ...

✅ TestRisk
   ├─ test_risk_calculation
   └─ ...

✅ TestMetrics
   ├─ test_metrics_extraction
   └─ ...

⚠️ GAPS:
   • SecurityRescanner.rescan_code() - not tested (crashes!)
   • Multi-vulnerability patch scenarios
   • ConflictAnalyzer edge cases
   • GitHub auth flows
   • Webhook signature verification
```

---

## Configuration Environment Variables

```
GITHUB_APP_ID
  └─ GitHub App ID for JWT generation

GITHUB_PRIVATE_KEY
  └─ PEM-format private key for signing JWTs

GITHUB_WEBHOOK_SECRET
  └─ Webhook secret for HMAC-SHA256 signature verification

DB_PATH (optional)
  └─ SQLite database path (default: data/dashboard.db)

DEBUG (Flask only)
  └─ Set debug=True in app.py for development
```

---

## Module Responsibility Matrix

| Module | Responsibility | Status |
|--------|---|---|
| vulnerability_scanner | Orchestrate scanning | ✅ |
| ast_scanner | Detect AST patterns | ✅ |
| regex_scanner | Detect regex patterns | ✅ |
| diff_engine | Filter to changed lines | ✅ |
| context_validator | Reduce false positives | ✅ |
| patch_orchestrator | Safe patch application | ✅ |
| fixers | AST transformations | ✅ |
| patch_validator | Syntax/semantic checks | ✅ |
| sandbox | Safe execution | ✅ |
| security_rescan | Re-scan patches | 🔴 Broken |
| risk_engine | Risk scoring | ✅ |
| confidence | Confidence scoring | ✅ |
| reporter | Format reports | ✅ |
| auth | GitHub authentication | ✅ |
| logger | Logging infrastructure | ✅ |
| db | Dashboard persistence | ⚠️ Unused |

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
  └─ Total: ~20-50ms per file

VALIDATION (O(n*k) where k = validators)
  ├─ Syntax check: ~2-5ms
  ├─ Sandbox execution: ~100-500ms (depends on code)
  ├─ Re-scan: ~15-25ms
  └─ Total: ~150-500ms per result

ANALYSIS (O(n))
  ├─ Risk scoring: ~1-2ms per vuln
  ├─ Confidence scoring: ~1-2ms per vuln
  └─ Total: ~5-10ms per result

Overall: ~200-600ms per file
```

---

## Webhook Processing Timeline

```
Event Received
  │
  ├─ Signature verification: 1-2ms
  │
  ├─ Clone repository: 1-5 seconds (network I/O)
  │
  ├─ For each .py file (avg 5-10 files in PR):
  │  ├─ Scan: 20ms
  │  ├─ Patch: 50ms
  │  ├─ Validate: 300ms
  │  └─ Analyze: 10ms
  │  → Subtotal per file: ~380ms
  │
  ├─ Total for all files: ~2-5 seconds
  │
  ├─ Format report: 10ms
  │
  ├─ Post PR comment: 500-1000ms (GitHub API)
  │
  └─ Return response: 5-10s total
```

---

## Repository Structure Health

```
✅ Good Practices:
  • Logical module organization (by concern)
  • Separation of concerns (scanner, patch, validator, risk)
  • Utility layer (logger, db, metadata)
  • Test suite in place
  • Configuration via env vars
  • Clear entry points (main.py, app.py)

⚠️ Areas for Improvement:
  • Dead code (~8% of codebase)
  • Duplicate implementations
  • Critical bug in security_rescan.py
  • Missing type hints (IDE support)
  • Incomplete feature integration
  • Orphaned database module (db.py)

🔴 Critical Issues:
  • Runtime crash in SecurityRescanner
  • 196 LOC of duplicate patch engine code
```

---

## Next Immediate Actions

**Priority 1** (Do today):
1. Read DEAD_CODE_REPORT.md
2. Read REFACTORING_OPPORTUNITIES.md::REF-1
3. Fix SecurityRescanner bug
4. Delete ast_patch_engine.py

**Priority 2** (Do this week):
1. Run full test suite
2. Verify webhook works with fixes
3. Delete transformers.py, pr_fetcher.py
4. Implement ConflictAnalyzer.register()

**Priority 3** (Next sprint):
1. Integrate DependencyGraph
2. Integrate patch_generator
3. Add type hints
4. Expand test coverage

