# Navigation — AI Risk Guard Project Map

## Project Structure

```
ai-risk-guard/
│
├── Plan.md                              # Roadmap
├── Deploy_Plan.md                       # Platform deployment (Render, Oracle Cloud)
├── README.md                            # Project overview, setup, env vars
├── AGENTS.md                            # Agent coding conventions + commands
├── requirements.txt                     # Python dependencies
├── pytest.ini                           # Test configuration (pythonpath=., testpaths=tests)
├── ruff.toml                            # Ruff lint config (py313)
├── .env.example                         # Environment variable template
├── .github/workflows/ci.yml             # CI: pytest + ruff + mypy + frontend build
│
├── app/
│   ├── main.py                          # CLI entry point + AIRiskGuard class
│   ├── app.py                           # Flask webhook + OAuth + REST API + SPA
│   └── metrics.py                       # Prometheus metrics
│
├── core/
│   ├── agents/                          # Multi-agent pipeline
│   │   ├── base_agent.py               # Abstract base agent
│   │   ├── manager_agent.py            # Pipeline orchestrator (per-file, thread-safe)
│   │   ├── scanner_agent.py            # Vulnerability scanning + test discovery
│   │   ├── patch_agent.py              # AST + Gemini patch generation
│   │   ├── validator_agent.py          # 5-stage validation
│   │   ├── risk_agent.py               # Risk/quality scoring + candidate selection
│   │   └── orchestrator_agent.py       # GitHub decisions + labels + SARIF
│   │
│   ├── scanner/                         # Scanning layer
│   │   ├── vulnerability_scanner.py    # Main scanner (10 vuln types)
│   │   ├── diff_engine.py              # Diff-aware scanning (is_new)
│   │   ├── context_validator.py        # False positive reduction
│   │   └── test_file_fetcher.py        # Test file + dependency discovery
│   │
│   ├── patch/                           # Patching layer
│   │   ├── fixers.py                   # AST transformers (fuzzy match)
│   │   ├── patch_orchestrator.py       # Conflict-safe multi-patch coordination
│   │   └── llm_patcher.py              # Gemini fallback chain + caching
│   │
│   ├── validator/                       # Validation layer
│   │   ├── patch_validator.py          # Syntax + import + policy + SSRF checks
│   │   ├── sandbox.py                  # Docker sandbox + local fallback
│   │   ├── security_rescan.py          # Re-scan patched code
│   │   └── test_rebind.py              # Test import rebinding
│   │
│   ├── risk/                            # Risk analysis layer
│   │   ├── risk_engine.py              # Weighted risk scoring (8 factors)
│   │   ├── context_engine.py           # Context-aware adjustments
│   │   └── metrics_extractor.py        # Code complexity metrics
│   │
│   ├── quality/                         # Patch quality scoring
│   │   └── patch_scorer.py             # 6 weighted factors
│   │
│   ├── confidence/                      # Confidence layer
│   │   ├── confidence.py               # Confidence scoring
│   │   └── learning_engine.py          # Historical learning from feedback
│   │
│   ├── policy/                          # Policy enforcement
│   │   └── policy_engine.py            # Organizational security policy
│   │
│   ├── config/                          # Pydantic v2 config models
│   │   ├── app_config.py               # Server/webhook/llm/sarif config
│   │   ├── risk_config.py              # Weights + gating thresholds
│   │   ├── policy_config.py            # Policy guardrails
│   │   ├── quality_config.py           # Quality weights
│   │   ├── sandbox_config.py           # Docker + local limits
│   │   └── __init__.py                 # ConfigRegistry singleton
│   │
│   ├── models/                          # Pydantic v2 data models
│   │   ├── vulnerability.py            # Vulnerability + VulnerabilityType + Severity
│   │   ├── analysis.py, patch.py       # Patch candidates/results
│   │   ├── risk.py, scan.py            # Risk + scan results
│   │   └── validation.py               # Validation stage results
│   │
│   ├── metadata/
│   │   ├── vuln_metadata.py            # Rule IDs, CVSS-like severities, CWE/OWASP
│   │   └── versions.py                 # Tool/engine version constants
│   │
│   ├── sarif/                           # SARIF 2.1.0 output
│   │   ├── converter.py                # Findings → risk assessments
│   │   ├── sarif_generator.py          # SARIF generation
│   │   └── sarif_writer.py             # SARIF writer
│   │
│   ├── cache/                           # SQLite-backed caches
│   │   ├── scan_cache.py               # Per-file scan results
│   │   ├── gemini_cache.py             # LLM prompt → output (SHA256)
│   │   ├── test_file_cache.py          # GitHub blob fetch cache (TTL)
│   │   ├── ast_cache.py                # Pickled AST trees (safe)
│   │   └── sandbox_cache.py            # In-proc sandbox results
│   │
│   ├── llm/                             # Gemini integration
│   │   └── model_resolver.py           # Model fallback resolution
│   │
│   ├── exceptions/                      # Typed exceptions
│   │   └── __init__.py                 # AIRiskGuardError hierarchy
│   │
│   ├── utils/                           # Core utilities
│   │   ├── tempdir.py                  # TempDir context manager
│   │   └── validation.py               # File/diff/code input validation
│   │
│   └── reporting/
│       └── explainer.py                # Human-readable explanations
│
├── services/github/                     # GitHub integration
│   ├── auth.py                          # JWT + installation tokens + OAuth
│   └── reporter.py                      # PR comments, labels, SARIF upload
│
├── utils/
│   ├── logger.py                        # JSON structured logging
│   ├── db.py                            # SQLite persistence (users, repos, scans, findings, caches)
│   └── retry.py                         # Retry with backoff
│
├── frontend/                            # React SPA
│   ├── src/
│   │   ├── main.jsx                     # React entry (BrowserRouter)
│   │   ├── App.jsx                      # Route definitions (14 routes)
│   │   ├── index.css                    # Design tokens + component classes
│   │   ├── api/client.js                # Axios API client
│   │   ├── components/                  # Navbar, Footer, Layout, PageHeader,
│   │   │                               #   ThemeToggle, ScrollReveal
│   │   ├── hooks/                       # useCountUp, useScrollReveal
│   │   └── pages/                       # Landing, Dashboard, Repositories, RepositoryDetail,
│   │                                   #   Scans, ScanDetail, FindingsExplorer, Metrics,
│   │                                   #   Pipeline, Policy, Settings, Status, Docs, Login
│   ├── index.html                       # Fonts (Sora, JetBrains Mono, Plus Jakarta Sans)
│   ├── vite.config.js                   # Dev :3000, proxy /api→:8000, build → ../static/frontend
│   ├── tailwind.config.js               # Custom palette + fonts
│   └── package.json
│
├── sandbox/
│   ├── Dockerfile.sandbox              # python:3.10-slim + pytest + non-root user
│   └── mock_header.py                  # Mock env + time.sleep patch header
│
├── config/
│   ├── app.yaml                         # Server, webhook, logging, sarif, llm chain
│   ├── risk.yaml                        # Weights + gating (8.5 / 4.0)
│   ├── quality.yaml                     # Quality weights
│   ├── sandbox.yaml                     # Docker + local fallback limits
│   └── policy/default.yaml              # Security policy guardrails
│
├── data/
│   ├── dashboard.db                     # SQLite database (runtime)
│   └── logs.json                        # JSON log output
│
├── static/frontend/                     # Built SPA (served by Flask)
│
├── tests/                               # 20 modules, ~550 tests
│   ├── conftest.py                      # pytest fixtures (mock Gemini)
│   ├── test_core.py                     # Detection + metadata
│   ├── test_features_345.py             # Vuln types + sanitizers + diff
│   ├── test_fixes_verification.py       # Fixer correctness
│   ├── test_orchestrator.py             # Gating decisions
│   ├── test_patch_agent.py / test_patch_validator.py
│   ├── test_policy*.py                  # Policy enforcement
│   ├── test_risk*.py                    # Risk scoring
│   ├── test_reporter.py                 # PR comment / SARIF
│   ├── test_github.py                   # JWT/OAuth
│   ├── test_sarif.py, test_summary.py   # SARIF + summary
│   ├── test_metrics.py                  # Prometheus metrics
│   ├── test_gemini_cache.py / test_llm_patcher.py
│   ├── test_ast_cache.py / test_retry.py
│   ├── test_test_fetcher.py / test_test_file_cache.py / test_test_rebind.py
│   ├── test_webhook_e2e.py              # Webhook → pipeline
│   ├── demo.py / demo_test.py           # Demo file + tests
│   └── ...
│
└── Documentation/
    ├── ARCHITECTURE_OVERVIEW.md         # System architecture
    ├── Proj_details.md                  # Project specification
    ├── PROJECT_STATUS.md                # Current completion status
    ├── VISUAL_REFERENCE_GUIDE.md        # Visual diagrams
    ├── COMPONENT_DEPENDENCY_MAP.md      # Module dependency map
    └── NAVIGATION.md                    # ← This file
```

---

## Key Documents Guide

| Document | What It Covers | Best For |
|----------|---------------|----------|
| `Plan.md` | Roadmap and feature planning | Planning what to build next |
| `Deploy_Plan.md` | Platform-by-platform deployment | Deploying to Render/Oracle Cloud |
| `README.md` | Setup, env vars, quick start | Onboarding a developer |
| `ARCHITECTURE_OVERVIEW.md` | System design, agents, pipeline | Understanding how it works |
| `Proj_details.md` | Full project spec, components, data models | Deep technical reference |
| `PROJECT_STATUS.md` | Current state, test results | Quick status check |

---

## Current Code Health

| Component | Status | Notes |
|-----------|--------|-------|
| Backend (all core modules) | ✅ Active | No dead modules, no broken imports |
| Frontend (React SPA) | ✅ Active | 14 pages, production build → `../static/frontend` |
| CI/CD (GitHub Actions) | ✅ Active | pytest + ruff + mypy + frontend build |
| Tests | ✅ ~550 passing | 20 test modules |

---

## Quick Reference: Entry Points

```bash
# CLI scan
python app/main.py path/to/file.py

# Webhook + API + SPA server (waitress)
python app/app.py                    # → http://localhost:8000

# Frontend dev server
cd frontend && npm run dev           # → http://localhost:3000 (proxies /api → :8000)

# Frontend production build (→ ../static/frontend)
cd frontend && npm run build

# Run tests
python -m pytest tests/ -x -q        # ~550 tests

# Lint + typecheck
ruff check .
mypy .
```

---

## API Endpoints (high-level)

```
GET  /api/health, /api/health/db, /api/health/gemini, /api/health/sandbox
GET  /api/dashboard, /api/metrics, /api/metrics/summary, /api/metrics/prometheus
GET  /api/repos, /api/repos/<id>, /api/repos/<id>/scans, /api/repos/<id>/findings
GET  /api/scans, /api/scans/<id>, /api/scans/<id>/findings
GET  /api/findings (filters/limit)
POST /api/findings/<id>/status, /api/feedback
GET  /api/policy, /api/settings (POST), /api/me
GET  /auth/login, /auth/callback, /auth/logout
POST /webhook
GET  /dashboard, / (SPA)
```
