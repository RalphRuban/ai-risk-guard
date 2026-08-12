# Component Dependency Map

## Module Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Entry Points                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  app/main.py (CLI)              app/app.py (Webhook + OAuth + SPA)     │
│  ↓                               ↓                                       │
│  ┌─────────────────────┐       ┌──────────────────────────────┐         │
│  │ AIRiskGuard()       │       │ Flask App (waitress :8000)   │         │
│  │  → ManagerAgent     │       │  - verify_signature()        │         │
│  └─────────────────────┘       │  - github_webhook()          │         │
│                                │  - OAuth login/callback      │         │
│                                │  - /api/* REST routes        │         │
│                                │  - SPA serving               │         │
│                                │ Dependencies:                │         │
│                                │  ├─ core/config (registry)   │         │
│                                │  ├─ core/models (Pydantic)   │         │
│                                │  ├─ app/main (AIRiskGuard)   │         │
│                                │  ├─ services/github/{auth,reporter}│   │
│                                │  ├─ utils/{db,logger,retry}  │         │
│                                │  └─ app/metrics (Prometheus) │         │
│                                └──────────────────────────────┘         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
    ┌──────────────────────────┐    ┌────────────────────────┐
    │ SCANNING PHASE           │    │ GITHUB SERVICES        │
    │ core/scanner/            │    │ services/github/       │
    └──────────────────────────┘    └────────────────────────┘
                    │                     │
        ┌───────────┼───────────┐        ├─ auth.py
        ▼           ▼           ▼        ├─ reporter.py
    ┌─────────┐ ┌────────┐ ┌─────────┐   └─ (SARIF upload)
    │   AST   │ │ Regex  │ │ Diff    │
    │ Scanner │ │Scanner │ │ Engine  │
    └─────────┘ └────────┘ └─────────┘
        │           │           │
        └───────────┼───────────┘
                    ▼
        ┌───────────────────────┐
        │ Context Validator     │
        │ (reduces false+)      │
        └───────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────────┐
    │ [Vulnerability] → List (Pydantic)│
    └──────────────────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────────┐
    │ PATCHING PHASE                   │
    │ core/patch/patch_orchestrator    │
    │  └─ fixers.apply_patch_to_content│
    │     (line-descending, conflicts) │
    │  + core/patch/llm_patcher        │
    │    (Gemini fallback chain)       │
    └──────────────────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────────┐
    │ VALIDATION PHASE                 │
    │ core/validator/                  │
    │ ├─ PatchValidator                │
    │ ├─ Sandbox (Docker/local)        │
    │ ├─ SecurityRescanner             │
    │ └─ test_rebind (pytest rebind)   │
    └──────────────────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────────┐
    │ ANALYSIS PHASE                   │
    ├──────────────────────────────────┤
    │ Risk Scoring (8 factors):        │
    │ ├─ risk_engine.compute_risk()    │
    │ ├─ context_engine                │
    │ └─ metrics_extractor             │
    │ Quality Scoring (6 factors):     │
    │ └─ quality/patch_scorer          │
    │ Confidence Scoring:              │
    │ ├─ confidence.calculate          │
    │ └─ learning_engine               │
    └──────────────────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────────┐
    │ REPORTING / ACTION PHASE         │
    │ services/github/reporter.py      │
    │ ├─ format_report()               │
    │ ├─ post_pr_comment()             │
    │ ├─ set_pr_labels()               │
    │ ├─ generate_sarif()              │
    │ └─ upload_sarif_to_code_scanning │
    └──────────────────────────────────┘
```

---

## Detailed Dependency Table

### Entry Points
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `app/app.py` | core/config, core/models, app/main, services/github (auth, reporter), utils (db, logger, retry), app/metrics | — (server) | ✅ Active |
| `app/main.py` | core/agents/manager_agent, core/scanner, core/patch, core/validator, core/risk, core/confidence, services/github/reporter | app/app.py, tests | ✅ Active |
| `app/metrics.py` | prometheus_client | app/app.py | ✅ Active |

### Core Config & Models
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `core/config/*` | pydantic v2, PyYAML | all core agents, app, tests | ✅ Active |
| `core/models/*` | pydantic v2 | scanner, patch, risk, reporter, tests | ✅ Active |
| `core/metadata/vuln_metadata.py` | (dict constants) | scanner, reporter, fixers, tests | ✅ Active |
| `core/metadata/versions.py` | (constants) | reporter, tests | ✅ Active |

### Scanner Layer
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `vulnerability_scanner.py` | ast, re, logger, vuln_metadata, context_validator, diff_engine | scanner_agent, tests | ✅ Active |
| `diff_engine.py` | re, logger | vulnerability_scanner, tests | ✅ Active |
| `context_validator.py` | re, logger | vulnerability_scanner, tests | ✅ Active |
| `test_file_fetcher.py` | requests/httpx, cache | scanner_agent, validator, tests | ✅ Active |

### Patch Layer
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `patch_orchestrator.py` | ast, difflib, logger | patch_agent, tests | ✅ Active |
| `fixers.py` | ast, difflib, logger, vuln_metadata | patch_agent, patch_orchestrator, tests | ✅ Active |
| `llm_patcher.py` | google-genai, core/llm, core/cache, logger | patch_agent, tests | ✅ Active |

### Validator Layer
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `patch_validator.py` | ast, re, logger | validator_agent, tests | ✅ Active |
| `sandbox.py` | subprocess, tempfile, os, docker, logger, sandbox_config | validator_agent, tests | ✅ Active |
| `security_rescan.py` | vulnerability_scanner, tempfile, os | validator_agent, tests | ✅ Active |
| `test_rebind.py` | re, ast | validator_agent, sandbox, tests | ✅ Active |

### Policy Layer
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `policy_engine.py` | core/config (policy), ast | risk_agent, validator_agent, tests | ✅ Active |

### Risk / Quality / Confidence Layer
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `risk/risk_engine.py` | logger, core/config (risk), context_engine, metrics_extractor | risk_agent, tests | ✅ Active |
| `risk/context_engine.py` | core/config | risk_engine | ✅ Active |
| `risk/metrics_extractor.py` | ast, logger | risk_engine, tests | ✅ Active |
| `quality/patch_scorer.py` | core/config (quality) | risk_agent, tests | ✅ Active |
| `confidence/confidence.py` | core/config, learning_engine | risk_agent, tests | ✅ Active |
| `confidence/learning_engine.py` | utils/db, datetime | confidence | ✅ Active |

### Agents
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `base_agent.py` | utils/logger, app/metrics | all agents | ✅ Active |
| `manager_agent.py` | scanner_agent, patch_agent, validator_agent, risk_agent | app/main, app/app | ✅ Active |
| `scanner_agent.py` | vulnerability_scanner, diff_engine, cache, test_file_fetcher, utils | manager_agent | ✅ Active |
| `patch_agent.py` | fixers, llm_patcher, patch_orchestrator, policy, cache | manager_agent | ✅ Active |
| `validator_agent.py` | patch_validator, sandbox, security_rescan, test_rebind, policy | manager_agent | ✅ Active |
| `risk_agent.py` | policy_engine, patch_scorer, risk_engine, confidence, quality | manager_agent | ✅ Active |
| `orchestrator_agent.py` | services/github/reporter (sarif, labels), core/config | manager_agent | ✅ Active |

### SARIF / Reporting
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `core/sarif/converter.py` | core/models | sarif_generator, tests | ✅ Active |
| `core/sarif/sarif_generator.py` | converter, metadata | reporter, orchestrator, tests | ✅ Active |
| `core/sarif/sarif_writer.py` | json, logger | reporter | ✅ Active |
| `core/reporting/explainer.py` | (dict constants) | reporter | ✅ Active |

### GitHub Services
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `auth.py` | jwt (PyJWT), time, requests, logger | app/app.py, reporter.py | ✅ Active |
| `reporter.py` | requests, logger, auth, core/sarif, metadata | app/app.py, orchestrator_agent | ✅ Active |

### Cache Layer (SQLite-backed)
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `scan_cache.py` | utils/db, hashlib | scanner_agent, tests | ✅ Active |
| `gemini_cache.py` | utils/db, hashlib | llm_patcher, tests | ✅ Active |
| `test_file_cache.py` | utils/db, datetime | test_file_fetcher, tests | ✅ Active |
| `ast_cache.py` | utils/db, RestrictedUnpickler | scanner, tests | ✅ Active |
| `sandbox_cache.py` | (in-proc dict) | sandbox, validator_agent | ✅ Active |

### Utilities
| Module | Imports From | Exported To | Status |
|--------|---|---|---|
| `utils/logger.py` | json, logging, sys, datetime | All modules | ✅ Active |
| `utils/db.py` | sqlite3, os, pathlib | app, agents, confidence, caches | ✅ Active |
| `utils/retry.py` | functools, time | reporter, llm_patcher | ✅ Active |

---

## Critical Paths (High-Traffic Dependencies)

```
Tier 1 (Core):
  ✓ core/config → All agents + app (configuration is centralized)
  ✓ core/models → scanner, patch, risk, reporter (typed data flow)
  ✓ utils/logger.py → All modules (ubiquitous)

Tier 2 (Main flow):
  ✓ vulnerability_scanner.py → scanner_agent → manager_agent
  ✓ fixers.py + llm_patcher.py → patch_agent → manager_agent
  ✓ sandbox.py + patch_validator.py → validator_agent → manager_agent
  ✓ risk_engine.py + patch_scorer.py → risk_agent → manager_agent
  ✓ reporter.py → orchestrator_agent + app.py

Tier 3 (Sub-dependencies):
  ✓ ContextValidator → vulnerability_scanner
  ✓ DiffAwareScanner → vulnerability_scanner
  ✓ SecurityRescanner → validator_agent
  ✓ policy_engine → risk_agent + validator_agent
  ✓ core/sarif → reporter + orchestrator_agent
```

---

## Circular Dependencies

✅ **None detected** — Graph is acyclic (DAG). `utils/logger` is a leaf-level dependency used ubiquitously but never imports upward.

---

## Unused/Dead Imports

- ✅ **None**. Removed: `ast_scanner.py`, `regex_scanner.py`, `entropy_detector.py`, `conflict_analyzer.py`, `patch_generator.py`, `dependency_graph.py`, `services/github/pr_fetcher.py`. All current modules are imported by the pipeline.

---

## Cross-Module Communication Pattern

```
┌─────────────────────────────────────────────────┐
│ PRIMARY: ManagerAgent pipeline (fresh per file)  │
├─────────────────────────────────────────────────┤
│ ManagerAgent.process_file():                     │
│   ctx = {file_path, pr_context, diff_data, ...}  │
│   ScannerAgent().execute(ctx)                    │
│   PatchAgent().execute(ctx)                      │
│   ValidatorAgent().execute(ctx)                  │
│   RiskAgent().execute(ctx)                       │
│   OrchestrationAgent().execute(ctx)              │
│                                                  │
│ Data flows through a shared context dict;        │
│ Pydantic models type the core objects.           │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ SECONDARY: Functional APIs                      │
├─────────────────────────────────────────────────┤
│ risk_engine.compute_risk(...) / explain_risk(..) │
│ confidence.calculate_confidence(...)            │
│ quality/patch_scorer.score(...)                 │
│ metrics_extractor.extract_metrics(...)          │
│ reporter.format_report(...) / post_pr_comment() │
└─────────────────────────────────────────────────┘
```

---

## Data Flow Through Pipeline

```
INPUT: File content + diff_data
  │
  ▼
VulnerabilityScanner.scan_file(...)
  │ AST parse → node visitor → 10 patterns
  │ regex secrets → diff-aware is_new → context validation
  ▼
OUTPUT: List[Vulnerability] (Pydantic)
  │
  ▼
PatchAgent → fixers.apply_patch_to_content (baseline_ast)
  │ + llm_patcher.generate (Gemini variants)
  │ apply_patches_safely (line-descending, conflict-safe)
  ▼
OUTPUT: patch candidates
  │
  ├──▶ PatchValidator.validate (syntax/imports/policy/ssrf)
  ├──▶ Sandbox.run (docker/local, limits, cache)
  ├──▶ test_rebind + pytest execution
  └──▶ SecurityRescanner.rescan_code
  ▼
For each candidate:
  ├──▶ quality/patch_scorer.score → quality (0-1)
  ├──▶ confidence.calculate_confidence + learning_engine
  ├──▶ risk_engine.compute_risk + explain_risk
  └──▶ Candidate ranking → winner
  ▼
OrchestrationAgent:
  ├──▶ Gating decision (COMMENT / REQUEST_CHANGES)
  ├──▶ set_pr_labels (security-risk-N)
  └──▶ generate_sarif + upload to Code Scanning
  ▼
reporter.format_report → PR comment
utils/db persistence + app/metrics update
```

---

## Dependency Health Metrics

| Metric | Value | Assessment |
|--------|---|---|
| Circular dependencies | 0 | ✅ Excellent |
| Dead modules | 0 | ✅ Excellent |
| Broken imports | 0 | ✅ Excellent |
| Max depth (import chain) | ~5 layers | ✅ Reasonable |
| Cohesion | High | ✅ Clear layers |
| Coupling | Low | ✅ Decoupled (agents, config, models) |
