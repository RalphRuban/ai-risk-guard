# AI Risk Guard - Complete Project Details (Proj_details)

**Document**: Project Specification & Implementation Roadmap  
**Version**: 1.0 (Phase 1 Focus)  
**Status**: Active Development  
**Last Updated**: 2026-06-10

---

## 📌 Executive Summary

**AI Risk Guard** is an intelligent GitHub-integrated security vulnerability detection and automated patch generation system for Python code. It combines AST analysis, machine learning feedback, and advanced validation to provide actionable security insights with high confidence.

**Vision**: Transform GitHub security workflows by automating vulnerability detection, intelligent patching, risk assessment, and continuous learning from patch outcomes.

**Target Users**: 
- Development teams (GitHub users)
- Security engineers
- DevOps/SRE teams
- Organizations seeking automated security scanning

---

## 🎯 Project Objectives

### Primary Objectives (TIER 1 - CORE)

1. **Automated Vulnerability Detection**
   - Detect common Python security vulnerabilities (4 types)
   - AST-based pattern matching for high accuracy
   - Diff-aware scanning to focus on changed code
   - Reduce false positives via context validation

2. **Intelligent Patch Generation**
   - Automatically generate secure patches
   - Multiple patch strategies (rule-based → ML-enhanced)
   - Explain WHY each patch is secure
   - Multi-candidate generation (choose safest option)

3. **Advanced Validation**
   - Sandboxed code execution (safe, controlled environment)
   - Syntax and semantic validation
   - Re-scan patched code for remaining vulnerabilities
   - Confidence scoring for each fix

4. **Risk Assessment**
   - Multi-factor risk calculation
   - Context-aware scoring
   - Severity weighting
   - Exposure and complexity analysis

5. **GitHub Integration**
   - Webhook-based triggering
   - Automatic PR comments with findings
   - GitHub App authentication
   - Seamless workflow integration

### Secondary Objectives (TIER 2 - DIFFERENTIATION)

6. **Intelligent Confidence Learning**
   - Track patch acceptance outcomes
   - Adapt confidence weights based on history
   - Self-improving system (learns from feedback)
   - Moves toward ML-assisted security

7. **Advanced Risk Model**
   - File criticality scoring
   - Code complexity hotspot detection
   - Change size impact analysis
   - Context-aware severity adjustment

8. **Professional Dashboard**
   - Real-time metrics visualization
   - Vulnerability trends
   - Patch success rates
   - Risk distribution analysis

9. **CI/CD Integration**
   - GitHub Actions support
   - Automated security gates
   - Policy enforcement
   - Deployment safety checks

10. **Production Readiness**
    - Comprehensive documentation
    - Docker containerization
    - Performance optimization
    - Security hardening

---

## 🏗️ System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│ GitHub (Event Source)                                       │
│ • PR created/updated                                        │
│ • Webhook triggered                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ AI Risk Guard System                                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  LAYER 1: INGESTION                                         │
│  ├─ Webhook handler (app/app.py)                           │
│  ├─ Signature verification (HMAC-SHA256)                   │
│  ├─ Repository cloning                                     │
│  └─ File discovery                                         │
│                                                              │
│  LAYER 2: SCANNING (core/scanner/)                         │
│  ├─ AST analysis (vulnerability patterns)                  │
│  ├─ Regex analysis (hardcoded secrets)                     │
│  ├─ Diff-aware filtering (changed lines only)              │
│  ├─ Entropy detection (random tokens)                      │
│  └─ Context validation (reduce false positives)            │
│                                                              │
│  LAYER 3: PATCHING (core/patch/)                           │
│  ├─ Patch generation (AST transformations)                 │
│  ├─ Multi-candidate ranking                                │
│  ├─ Conflict detection                                     │
│  └─ Safe patch application (transactional)                 │
│                                                              │
│  LAYER 4: VALIDATION (core/validator/)                     │
│  ├─ Syntax validation                                      │
│  ├─ Sandbox execution (mode: compile/safe-run/exec)        │
│  ├─ Security re-scan                                       │
│  └─ Semantic validation                                    │
│                                                              │
│  LAYER 5: ANALYSIS (core/risk/ + core/confidence/)         │
│  ├─ Risk scoring (multi-factor weighted)                   │
│  ├─ Confidence calculation                                 │
│  ├─ Metrics extraction (complexity, LOC)                   │
│  └─ Context-aware adjustments                              │
│                                                              │
│  LAYER 6: LEARNING (core/confidence/)                      │
│  ├─ Feedback collection                                    │
│  ├─ Historical tracking                                    │
│  ├─ Confidence adaptation                                  │
│  └─ Success rate calculation                               │
│                                                              │
│  LAYER 7: REPORTING (services/github/)                     │
│  ├─ Vulnerability explanation                              │
│  ├─ Patch suggestion formatting                            │
│  ├─ PR comment generation                                  │
│  └─ GitHub API integration                                 │
│                                                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Output: PR Comment with Findings + Suggestions              │
│ • Vulnerability details (type, line, severity)             │
│ • Proposed patch code                                       │
│ • Risk score (0-10)                                         │
│ • Confidence percentage                                     │
│ • Validation status                                         │
│ • Feedback link                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Complete Workflow

### User Perspective (Happy Path)

```
Step 1: Developer Creates PR
├─ Writes code
├─ Commits to feature branch
└─ Opens PR

Step 2: AI Risk Guard Triggered
├─ GitHub sends webhook
├─ System clones repository
├─ Analyzes all Python files

Step 3: Vulnerability Detected
├─ Identifies insecure patterns
├─ Determines severity
├─ Calculates risk

Step 4: Patch Generated
├─ Creates secure fix
├─ Validates syntax
├─ Tests in sandbox

Step 5: Risk Assessed
├─ Multi-factor calculation
├─ Confidence scoring
├─ Context analysis

Step 6: PR Comment Posted
├─ Shows findings
├─ Suggests patches
├─ Explains risks

Step 7: Developer Reviews
├─ Reads feedback
├─ Accepts patch suggestion
├─ Applies fix

Step 8: Feedback Recorded
├─ System learns outcome
├─ Updates confidence weights
├─ Improves future detections

Step 9: Dashboard Updated
├─ Metrics incremented
├─ Trends calculated
├─ Analytics recorded
```

---

## 📦 Component Breakdown

### Core Modules (27 components)

#### SCANNER LAYER (6 modules)
```
core/scanner/
├── vulnerability_scanner.py   (main orchestrator)
├── ast_scanner.py             (AST pattern matching)
├── regex_scanner.py           (regex-based secrets)
├── diff_engine.py             (diff-aware filtering)
├── context_validator.py       (reduce false positives)
└── entropy_detector.py        (entropy-based detection)
```

**Responsibility**: Detect all vulnerabilities in code  
**Input**: File path or code string  
**Output**: List[Dict with vulnerability details]

---

#### PATCH LAYER (7 modules - will be consolidated)
```
core/patch/
├── patch_orchestrator.py      (safe multi-patch coordination)
├── fixers.py                  (AST transformations - canonical)
├── conflict_analyzer.py       (detect patch conflicts)
├── dependency_graph.py        (topological ordering)
├── patch_generator.py         (human-readable patches)
├── ast_patch_engine.py        (DEPRECATED - delete)
└── transformers.py            (UNUSED - delete)
```

**Responsibility**: Generate and apply secure patches  
**Input**: Code + list of vulnerabilities  
**Output**: Patched code + diff + metadata

---

#### VALIDATOR LAYER (3 modules)
```
core/validator/
├── patch_validator.py         (syntax/semantic checks)
├── sandbox.py                 (safe code execution)
└── security_rescan.py         (vulnerability re-scan - HAS BUG)
```

**Responsibility**: Verify patches are safe and effective  
**Input**: Patched code  
**Output**: Validation results + sandbox output

---

#### RISK LAYER (3 modules)
```
core/risk/
├── risk_engine.py             (weighted risk calculation)
├── context_engine.py          (context-aware adjustments)
└── metrics_extractor.py       (code metrics extraction)
```

**Responsibility**: Assess risk and impact  
**Input**: Vulnerability + patch + validation results  
**Output**: Risk score (0-10) + breakdown

---

#### CONFIDENCE LAYER (2 modules)
```
core/confidence/
├── confidence.py              (confidence scoring)
└── learning_engine.py         (historical learning)
```

**Responsibility**: Estimate fix reliability  
**Input**: Vulnerability + patch + validation + history  
**Output**: Confidence score (0.0-1.0)

---

#### REPORTING LAYER (3 modules)
```
core/reporting/explainer.py    (generate explanations)
services/github/
├── reporter.py                (format PR comments)
├── auth.py                    (GitHub App authentication)
└── pr_fetcher.py              (UNUSED - delete)
```

**Responsibility**: Communicate findings to users  
**Input**: Analysis results  
**Output**: PR comment + feedback tracking

---

#### APPLICATION LAYER (2 modules)
```
app/
├── main.py                    (CLI orchestrator)
├── app.py                     (Flask webhook server)
└── config.py                  (UNUSED - delete)
```

**Responsibility**: Application entry points  
**Input**: File path (CLI) or webhook (HTTP)  
**Output**: Formatted report

---

#### UTILITIES (2 modules)
```
utils/
├── logger.py                  (JSON structured logging)
└── db.py                      (SQLite persistence - not integrated)
```

---

## 🎨 Data Models

### Vulnerability Object
```python
{
    "type": "COMMAND_INJECTION",        # One of 4 types
    "file": "src/app.py",
    "line": 42,
    "column": 10,
    "severity": "HIGH",                 # HIGH/MEDIUM/LOW
    "description": "Unsafe shell execution",
    "context": "os.system(user_input)",
    "cwe": "CWE-78",
    "owasp": "A03:2021 – Injection"
}
```

### Analysis Result Object
```python
{
    "vulnerability": {... Vulnerability ...},
    "patch": "patched code string",
    "diff": "unified diff format",
    "validation": {
        "success": bool,
        "syntax_valid": bool,
        "semantic_valid": bool,
        "errors": [str]
    },
    "sandbox": {
        "success": bool,
        "output": str,
        "errors": [str],
        "execution_time_ms": int
    },
    "rescan": {
        "success": bool,
        "remaining_vulnerabilities": [...]
    },
    "confidence": 0.85,                 # 0.0-1.0
    "risk": 7.2,                        # 0.0-10.0
    "risk_breakdown": {
        "severity": 0.95,
        "type": 0.90,
        "validation": 0.92,
        "complexity": 0.78,
        "sensitivity": 0.85,
        "exposure": 0.75
    }
}
```

---

## 🔐 Vulnerability Types Covered

| Type | Example | Fix Strategy | Severity |
|------|---------|---|---|
| COMMAND_INJECTION | `os.system(user_input)` | Use subprocess with shell=False | HIGH |
| CODE_INJECTION | `eval(user_input)` | Use ast.literal_eval() | HIGH |
| HARDCODED_SECRET | `PASSWORD = os.getenv("PASSWORD")` | Move to environment var | HIGH |
| INSECURE_DESERIALIZATION | `pickle.loads(data)` | Use json.loads() | HIGH |

---

## 🎯 Phase 1 Roadmap (45 Days)

### Week 1: Stabilization & Refactoring
**Goal**: Clean architecture, remove dead code, fix bugs

- [ ] Fix SecurityRescanner import bug
- [ ] Delete ast_patch_engine.py (duplicate)
- [ ] Delete transformers.py (unused)
- [ ] Remove pr_fetcher.py (unused)
- [ ] Clean project structure
- [ ] Centralize error handling
- [ ] Improve logging coverage

**Deliverable**: Production-ready codebase (no crashes)

---

### Week 2: Advanced Validation Sandbox (Level 1.5)
**Goal**: Enhanced sandbox with multiple execution modes

- [ ] Add "compile" mode (parse-only)
- [ ] Add "safe-run" mode (restricted execution)
- [ ] Implement memory limits
- [ ] Add configurable timeouts
- [ ] Resource profiling
- [ ] Improve error messages

**Deliverable**: Sandbox supports 3 execution modes + resource control

---

### Week 3: Multi-Factor Risk Model
**Goal**: Sophisticated risk calculation from multiple dimensions

- [ ] Integrate Radon (complexity analysis)
- [ ] Implement code complexity scoring
- [ ] Add file sensitivity detection
- [ ] Calculate exposure metrics
- [ ] Combine all 7 factors
- [ ] Add context-aware adjustments
- [ ] Create risk explanation engine

**Deliverable**: Risk scores reflect true impact (not just severity)

---

### Week 4: Feedback Learning System
**Goal**: Adaptive system that improves from outcomes

- [ ] Create POST /feedback endpoint
- [ ] Integrate database (db.py)
- [ ] Implement feedback storage
- [ ] Wire learning engine
- [ ] Update confidence calculation
- [ ] Add feedback UI/form
- [ ] Create feedback analytics

**Deliverable**: System learns from patch outcomes + improves over time

---

### Week 5: Advanced Dashboard
**Goal**: Professional metrics visualization

- [ ] Setup React frontend
- [ ] Create API endpoints (/api/metrics, /api/trends, etc.)
- [ ] Build Chart.js visualizations
- [ ] Implement real-time metrics
- [ ] Create trend charts
- [ ] Build vulnerability table
- [ ] Deploy dashboard UI

**Deliverable**: Interactive dashboard showing security metrics + trends

---

### Week 6: Integration & Expo Preparation
**Goal**: Production deployment + presentation readiness

- [ ] Setup GitHub Actions workflow
- [ ] Create comprehensive README
- [ ] Add architecture diagrams
- [ ] Document API endpoints
- [ ] Prepare demo scenarios
- [ ] Create demo script
- [ ] Setup deployment (Docker/Cloud)
- [ ] Final testing

**Deliverable**: Production-ready system ready for presentation

---

## 🛠️ Technology Stack

### Core Languages
- **Python 3.9+** (main)
- **JavaScript/TypeScript** (React frontend)
- **YAML** (GitHub Actions)
- **SQL** (SQLite)

### Key Libraries

| Category | Libraries | Purpose |
|----------|-----------|---------|
| **Web** | Flask, FastAPI | Webhook server + API |
| **AST Analysis** | ast module, radon | Code analysis + complexity |
| **GitHub** | PyJWT, PyGithub, requests | GitHub App integration |
| **Security** | cryptography, PyNaCl | Encryption + HMAC |
| **Data** | pandas, numpy | Metrics + analytics |
| **ML (Future)** | scikit-learn, xgboost, shap | ML-based patch generation |
| **Testing** | pytest | Unit + integration tests |
| **Frontend** | React, Chart.js | Dashboard UI |

---

## 📊 Success Metrics

### Correctness Metrics
- ✅ Detection rate: >90% for seeded vulnerabilities
- ✅ False positive rate: <10%
- ✅ Patch success rate: >85% syntactically valid

### System Metrics
- ✅ Response time: <5 seconds per file
- ✅ Webhook reliability: 99%+ uptime
- ✅ Database performance: <100ms query time

### Quality Metrics
- ✅ Test coverage: >80%
- ✅ Documentation: Complete (API + architecture)
- ✅ Code health: Zero critical bugs

### Learning Metrics (Week 4+)
- ✅ Confidence accuracy: Improves 5% per week from feedback
- ✅ Patch adaptation: Learns from acceptance patterns
- ✅ Risk prediction: Correlates with actual impact

---

## 🚀 Deployment Architecture

### Current (Phase 1)
```
GitHub PR
    ↓
Webhook → Flask Server (port 8000)
    ↓
Process PR
    ↓
Post Comment
```

### Production Target
```
GitHub PR
    ↓
Webhook → Load Balancer
    ↓
┌─────────────┬─────────────┐
│  Container  │  Container  │
│  Instance 1 │  Instance 2  │
└─────────────┴─────────────┘
    ↓
Database (PostgreSQL or DynamoDB)
    ↓
Dashboard (S3 + CloudFront or Vercel)
```

---

## 🔒 Security Considerations

### Input Validation
- ✅ HMAC-SHA256 webhook signature verification
- ✅ GitHub API token scoping
- ✅ Code sandbox isolation

### Secret Management
- ✅ Environment variable storage
- ✅ No hardcoded credentials
- ✅ Private key encryption

### Code Execution Safety
- ✅ Sandboxed execution (no file system access)
- ✅ Memory limits
- ✅ Timeout enforcement
- ✅ Restricted Python builtins

---

## 📈 Scalability Plan

### Phase 1 (Current)
- Single webhook server
- Local file processing
- SQLite database

### Phase 2 (Post-Phase-1)
- Load-balanced servers
- Cache layer (Redis)
- PostgreSQL database
- Async task queue (Celery)

### Phase 3 (Future)
- Microservices architecture
- ML pipeline (separate service)
- Multi-language support
- Enterprise SaaS features

---

## 🧪 Testing Strategy

### Unit Tests
- Scanner: Test each vulnerability type detection
- Patcher: Test each fix strategy
- Validator: Test validation modes
- Risk Engine: Test scoring calculations

### Integration Tests
- End-to-end scanning + patching workflow
- Sandbox execution + error handling
- Database operations
- GitHub API interactions

### Performance Tests
- Large file handling (>1MB)
- Many vulnerabilities (100+)
- Concurrent webhook processing

### Security Tests
- Malicious code in sandbox
- HMAC signature bypass attempts
- Secret extraction attempts

---

## 📚 Documentation Plan

### User Documentation
- [ ] Installation guide (local + cloud)
- [ ] Configuration reference
- [ ] API documentation (Swagger/OpenAPI)
- [ ] GitHub integration guide

### Technical Documentation
- [ ] Architecture overview (this doc)
- [ ] Component design documents
- [ ] Database schema
- [ ] Deployment guide

### Demo Documentation
- [ ] Walkthrough scenarios
- [ ] Screenshot gallery
- [ ] Video demo script
- [ ] FAQ document

---

## 🎓 Learning Outcomes

**What This Project Teaches**:

1. **Security**
   - Vulnerability detection techniques
   - Secure code generation
   - Sandbox design patterns
   - Cryptographic verification

2. **Systems Design**
   - Layered architecture
   - Event-driven processing
   - Real-time analytics
   - Learning systems

3. **Engineering**
   - Code refactoring
   - Testing strategies
   - Performance optimization
   - Deployment automation

4. **Product Thinking**
   - User workflows
   - Iterative improvement
   - Feedback loops
   - Dashboard design

---

## 🎬 Success Story (Post-Phase 1)

**Day 1**: 
- Developer creates PR with unsafe `os.system()` call
- Workflow triggers AI Risk Guard

**Moment of Magic**:
1. System scans code (2 seconds)
2. Finds vulnerability (99% confidence)
3. Generates 3 patch candidates
4. Validates in sandbox (all pass)
5. Calculates risk: 7.8/10
6. Posts detailed PR comment

**Result**:
- Developer sees exact fix
- Applies patch
- Re-submits PR
- Green checkmark ✅
- Fast merge

---

## 💰 Business Value

### For Users
- **Security**: Faster vulnerability discovery
- **Developer Experience**: Automatic patch suggestions
- **Learning**: Understands fixes (not just copy-paste)
- **Time**: Reduces security review time by 50%

### For Organizations
- **Compliance**: Automated security gates
- **Risk Management**: Multi-factor risk assessment
- **Metrics**: Vulnerability trends + dashboards
- **Culture**: Builds security-first mindset

### For This Project
- **Portfolio**: Top-tier security tool
- **Impact**: Real-world applicable system
- **Scalability**: Foundation for enterprise product
- **Research**: Learning systems + feedback loops

---

## 🏆 Differentiation Factors

**Why This Project Stands Out**:

1. ✅ **End-to-End System** (not toy project)
   - Scanner → Patcher → Validator → Risk → Reporting
   - Integrated GitHub workflow

2. ✅ **Learning Capability** (moves toward ML)
   - Feedback loops
   - Adaptive confidence
   - Historical tracking

3. ✅ **Production Features**
   - Dashboard + metrics
   - CI/CD integration
   - Professional documentation

4. ✅ **Research Elements**
   - Multi-factor risk model
   - Sandbox design
   - Learning engine

5. ✅ **Scalability** (not just MVP)
   - Modular architecture
   - Containerizable
   - Cloud-deployment ready

---

## 📋 Final Checklist (Phase 1 Complete)

### Must-Have
- [ ] No critical bugs (SecurityRescanner fixed)
- [ ] All unit tests passing
- [ ] Clean code (no duplicates)
- [ ] Professional documentation
- [ ] GitHub integration working

### Should-Have
- [ ] Dashboard deployed
- [ ] Feedback system working
- [ ] Multi-factor risk active
- [ ] GitHub Actions configured

### Nice-to-Have
- [ ] Docker container
- [ ] Performance optimized
- [ ] Comprehensive demo
- [ ] Video tutorial

---

## 🎯 Conclusion

**AI Risk Guard** is positioned to be a **top-tier university project** that demonstrates:

✅ **Technical Excellence**: Clean architecture, advanced patterns  
✅ **Problem Solving**: Real-world security challenges  
✅ **Product Thinking**: User experience + scalability  
✅ **Research**: Learning systems + feedback loops  
✅ **Execution**: Complete 45-day implementation plan  

**The result**: A system that looks and acts like a **startup product**, not a student assignment.

