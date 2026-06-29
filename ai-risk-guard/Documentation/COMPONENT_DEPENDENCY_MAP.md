# Component Dependency Map

## Module Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Entry Points                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  app/main.py (CLI)              app/app.py (Webhook Server)            │
│  ↓                               ↓                                       │
│  ┌─────────────────────┐       ┌──────────────────────────────┐         │
│  │ AIRiskGuard()       │       │ Flask App                    │         │
│  │  initialize:        │       │  - verify_signature()        │         │
│  │  ├─ scanner         │       │  - github_webhook()          │         │
│  │  ├─ validator       │       │  - health()                  │         │
│  │  ├─ rescanner       │       │                              │         │
│  │  └─ sandbox         │       │ Dependencies:                │         │
│  └─────────────────────┘       │  ├─ services/github/auth.py │         │
│                                 │  ├─ main.AIRiskGuard        │         │
│  Exported methods:              │  └─ services/github/reporter│         │
│  └─ analyze_file()              └──────────────────────────────┘         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
    ┌──────────────────────────┐    ┌────────────────────────┐
    │ SCANNING PHASE           │    │ GITHUB SERVICES        │
    │ core/scanner/            │    │ services/github/       │
    └──────────────────────────┘    └────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
    ┌─────────┐ ┌────────┐ ┌─────────────┐
    │   AST   │ │ Regex  │ │ Diff        │
    │ Scanner │ │Scanner │ │ Engine      │
    └─────────┘ └────────┘ └─────────────┘
        │           │           │
        └───────────┼───────────┘
                    ▼
        ┌───────────────────────┐
        │ Context Validator     │ ◄─── Entropy Detector
        │ (reduces false+)      │
        └───────────────────────┘
                    ▼
    ┌──────────────────────────────────┐
    │ [Vulnerability Objects] → List   │
    └──────────────────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────────┐
    │ PATCHING PHASE                   │
    │ core/patch/patch_orchestrator    │
    │  ├─ ConflictAnalyzer             │
    │  └─ fixers.apply_patch_to_content│
    └──────────────────────────────────┘
                    ▼
    ┌──────────────────────────────────┐
    │ VALIDATION PHASE                 │
    │ core/validator/                  │
    │ ├─ PatchValidator                │
    │ ├─ Sandbox                       │
    │ └─ SecurityRescanner             │
    │    (re-scan for vulns)           │
    └──────────────────────────────────┘
                    ▼
    ┌──────────────────────────────────┐
    │ ANALYSIS PHASE                   │
    ├──────────────────────────────────┤
    │ Risk Scoring:                    │
    │ ├─ calculate_risk()              │
    │ ├─ ContextRiskEngine             │
    │ └─ extract_metrics()             │
    │                                  │
    │ Confidence Scoring:              │
    │ ├─ calculate_confidence()        │
    │ └─ ConfidenceLearningEngine      │
    └──────────────────────────────────┘
                    ▼
    ┌──────────────────────────────────┐
    │ REPORTING PHASE                  │
    │ services/github/reporter.py      │
    │ ├─ format_report()               │
    │ ├─ SecurityExplainer             │
    │ └─ post_pr_comment()             │
    └──────────────────────────────────┘
```

---

## Detailed Dependency Table

### Scanner Layer
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `vulnerability_scanner.py` | logger, vuln_metadata, ContextValidator, DiffAwareScanner, ASTScanner, RegexScanner | main.AIRiskGuard, test_core.py | ✅ Active |
| `ast_scanner.py` | logger, vuln_metadata | vulnerability_scanner.py | ✅ Active |
| `regex_scanner.py` | vuln_metadata, EntropyDetector, ContextValidator | vulnerability_scanner.py | ✅ Active |
| `diff_engine.py` | logger | vulnerability_scanner.py, app.py | ✅ Active |
| `context_validator.py` | logger | vulnerability_scanner.py, regex_scanner.py, test_core.py | ✅ Active |
| `entropy_detector.py` | (std lib only) | regex_scanner.py | ✅ Active |

### Patch Layer
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `patch_orchestrator.py` | difflib, ConflictAnalyzer | main.AIRiskGuard | ✅ Active |
| `fixers.py` | ast, difflib, logger | main.AIRiskGuard, test_core.py | ✅ Active |
| `ast_patch_engine.py` | ast, difflib | ❌ NOT IMPORTED | ⚠️ Dead |
| `conflict_analyzer.py` | (std lib only) | patch_orchestrator.py | ✅ Active |
| `patch_generator.py` | Sandbox | ❌ NOT IMPORTED | ⚠️ Dead |
| `dependency_graph.py` | defaultdict | ❌ NOT IMPORTED | ⚠️ Dead |
| `transformers.py` | ast | ❌ NOT IMPORTED | ⚠️ Dead |

### Validator Layer
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `patch_validator.py` | ast, re | main.AIRiskGuard | ✅ Active |
| `sandbox.py` | subprocess, tempfile, logger | main.AIRiskGuard, patch_generator.py | ✅ Active |
| `security_rescan.py` | vulnerability_scanner (❌ BUG), tempfile, os | main.AIRiskGuard | 🔴 Broken |

### Risk/Confidence Layer
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `risk_engine.py` | logger, ContextRiskEngine | main.AIRiskGuard, test_core.py | ✅ Active |
| `context_engine.py` | (empty) | risk_engine.py | ✅ Active |
| `metrics_extractor.py` | ast, logger | main.AIRiskGuard, test_core.py | ✅ Active |
| `confidence.py` | ConfidenceLearningEngine | main.AIRiskGuard, test_core.py | ✅ Active |
| `learning_engine.py` | defaultdict | confidence.py | ✅ Active |

### Reporting Layer
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `explainer.py` | (dict constants only) | reporter.py | ✅ Active |
| `reporter.py` | requests, logger, SecurityExplainer, VULN_METADATA | main.AIRiskGuard, app.py | ✅ Active |
| `pr_fetcher.py` | requests, logger | ❌ NOT IMPORTED | ⚠️ Dead |

### Authentication
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `auth.py` | time, jwt, requests, logger | app.py | ✅ Active |

### Utilities
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `logger.py` | json, logging, sys, datetime | All modules | ✅ Active |
| `db.py` | sqlite3, os, pathlib | ❌ NOT IMPORTED | ⚠️ Unused in runtime |
| `vuln_metadata.py` | (dict only) | scanner, reporter, fixers | ✅ Active |

---

## Critical Paths (High-Traffic Dependencies)

```
Tier 1 (Core):
  ✓ logger.py → All modules (ubiquitous)
  ✓ vuln_metadata.py → scanner, fixers, reporter

Tier 2 (Main flow):
  ✓ vulnerability_scanner.py → main.AIRiskGuard
  ✓ patch_orchestrator.py → main.AIRiskGuard
  ✓ patch_validator.py → main.AIRiskGuard
  ✓ risk_engine.py → main.AIRiskGuard
  ✓ reporter.py → app.py & main.AIRiskGuard

Tier 3 (Sub-dependencies):
  ✓ ContextValidator → vulnerability_scanner, regex_scanner
  ✓ DiffAwareScanner → vulnerability_scanner
  ✓ Sandbox → patch_validator (indirectly)
  ✓ ContextRiskEngine → risk_engine
```

---

## Circular Dependencies

✅ **None detected** - Graph is acyclic (DAG)

---

## Unused/Dead Imports in Active Modules

### `security_rescan.py` (🔴 CRITICAL)
```python
from core.scanner.vulnerability_scanner import scanner  # Line 6
scanner.scan_file(path)  # Line 7 - UNDEFINED, scanner is MODULE not INSTANCE
```
**Impact**: Module crashes when `SecurityRescanner.rescan_code()` is called
**Fix**: Should be:
```python
from core.scanner.vulnerability_scanner import VulnerabilityScanner
scanner = VulnerabilityScanner()
```

### Other Unused Imports
- None critical in active modules

---

## Cross-Module Communication Pattern

```
┌─────────────────────────────────────────────────┐
│ PRIMARY PATTERN: Dependency Injection            │
├─────────────────────────────────────────────────┤
│ main.AIRiskGuard.__init__():                     │
│   self.scanner = VulnerabilityScanner()          │
│   self.validator = PatchValidator()              │
│   self.rescanner = SecurityRescanner()           │
│   self.sandbox = Sandbox()                       │
│                                                  │
│ main.AIRiskGuard.analyze_file():                 │
│   self.scanner.scan_file()                       │
│   apply_patches_safely(vuln_list)               │
│   self.validator.validate_all()                  │
│   self.sandbox.run()                            │
│   self.rescanner.rescan_code()                  │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ SECONDARY: Functional API (no classes)           │
├─────────────────────────────────────────────────┤
│ risk_engine:                                     │
│   calculate_risk(vuln, pr, confidence, ...)     │
│   explain_risk(vuln, pr, confidence, ...)       │
│                                                  │
│ confidence:                                      │
│   calculate_confidence(vuln, patch, ...)        │
│                                                  │
│ metrics_extractor:                              │
│   extract_metrics(file_path) → dict             │
│                                                  │
│ reporter:                                        │
│   format_report(results) → markdown             │
│   post_pr_comment(repo, pr, results, token)     │
└─────────────────────────────────────────────────┘
```

---

## Data Flow Through Pipeline

```
INPUT: File path (string)
  │
  ▼
VulnerabilityScanner.scan_file(file_path)
  │ Reads file
  │ Parses AST
  │ Applies scanners
  ▼
OUTPUT: vulnerabilities: List[Dict]
  [{
    "type": "COMMAND_INJECTION",
    "file": "app.py",
    "line": 42,
    ...
  }, ...]
  │
  ▼
apply_patches_safely(code, vulnerabilities, patch_fn)
  │ Sorts by line (reverse)
  │ Checks conflicts
  │ Applies AST transforms
  ▼
OUTPUT: patch_result: Dict
  {
    "final_code": "patched Python source",
    "combined_diff": "unified diff",
    "applied": [...],
    "errors": [...]
  }
  │
  ├──▶ PatchValidator.validate_all(patched_code)
  │    ▼ OUTPUT: validation: Dict
  │
  ├──▶ Sandbox.run(patched_code)
  │    ▼ OUTPUT: sandbox: Dict
  │
  └──▶ SecurityRescanner.rescan_code(patched_code)
       ▼ OUTPUT: rescan: Dict
  │
  ▼
For each vulnerability:
  │
  ├──▶ calculate_confidence(vuln, patch, validation)
  │    ▼ confidence: float [0.0-1.0]
  │
  ├──▶ calculate_risk(vuln, pr, confidence, validation, metrics)
  │    ▼ risk: float [0.0-10.0]
  │
  └──▶ explain_risk(...)
       ▼ risk_breakdown: Dict
  │
  ▼
Assemble result for this vulnerability
  result: {
    "vulnerability": Dict,
    "patch": str,
    "diff": str,
    "validation": Dict,
    "sandbox": Dict,
    "rescan": Dict,
    "confidence": float,
    "risk": float,
    "risk_breakdown": Dict
  }
  │
  ▼
OUTPUT: List[result]
  │
  ▼
format_report(results) → markdown string
  │
  ▼
post_pr_comment(repo, pr, results, token) → HTTP POST to GitHub
```

---

## Import Count by Module

| Module | External Imports | Internal Imports | Total |
|--------|---|---|---|
| app.py | 13 (os, hmac, hashlib, tempfile, subprocess, flask, dotenv, ...) | 5 (main, auth, reporter, diff_engine) | 18 |
| main.py | 0 | 10 (logger, scanner, patch_orch, fixers, validator, rescanner, sandbox, confidence, risk, reporter) | 10 |
| vulnerability_scanner.py | 4 (ast, os, re, logger) | 4 (vuln_metadata, ContextValidator, DiffAwareScanner, ...) | 8 |
| **Average** | ~2-3 | ~2-3 | ~5 |

---

## Dependency Health Metrics

| Metric | Value | Assessment |
|--------|---|---|
| Circular dependencies | 0 | ✅ Excellent |
| Dead modules | 4 | ⚠️ Moderate (8% of code) |
| Broken imports | 1 🔴 | ⚠️ Critical |
| Max depth (import chain) | ~6 layers | ✅ Reasonable |
| Cohesion | High | ✅ Clear layers |
| Coupling | Low | ✅ Decoupled |

