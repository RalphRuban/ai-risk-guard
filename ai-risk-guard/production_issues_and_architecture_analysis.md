# AI Risk Guard — Security & Architecture Audit Report

This document contains a comprehensive analysis of the **design architecture**, **core build**, and **production issues** identified within the AI Risk Guard project. No code modifications were performed during this audit, in accordance with your guidelines.

---

## 1. Design & System Architecture Analysis

AI Risk Guard is designed as a **hybrid static-analysis and dynamic-sandboxed validation platform** that scans GitHub Pull Requests for vulnerabilities, generates AI-driven patches, and provides context-aware risk scores.

### Backend Architecture (Flask & SQLite)
- **Zero-Cost Code Ingestion**: The ingestion engine ([app.py](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/app/app.py#L459-L818)) retrieves files modified in a PR dynamically via the GitHub Contents API without performing a resource-heavy `git clone` to disk.
- **Multi-Level Scanning**:
  1. **AST Scanner** ([vulnerability_scanner.py](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/core/scanner/vulnerability_scanner.py)): Constructs local ASTs to search for known vulnerability signatures (SQLi, Command Injection, Insecure Deserialization, SSRF).
  2. **Sandbox Validation** ([sandbox.py](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/core/validator/sandbox.py)): Runs the modified code alongside fetched regression tests inside an isolated Docker container ([Dockerfile.sandbox](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/sandbox/Dockerfile.sandbox)) to test candidate patches.
- **Context-Aware Risk Engine**: Combines severity, code complexity, target directory sensitivity, and sandboxed test validation outcomes to calculate a final weighted risk score out of 10 ([risk_engine.py](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/core/risk/risk_engine.py)).
- **Multi-Tenant SQLite Database**: Utilizes an SQLite database configured in WAL mode ([db.py](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/utils/db.py#L14-L23)) with schema isolation that associates repositories and scans with specific users logged in via GitHub OAuth.

### Frontend Architecture (React 18 & Vite SPA)
- Constructed as a modern React application compiled into the backend's static directory.
- Features dynamic dashboards ([Dashboard.jsx](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/frontend/src/pages/Dashboard.jsx)), scan logs ([ScanDetail.jsx](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/frontend/src/pages/ScanDetail.jsx)), and configuration panels ([Settings.jsx](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/frontend/src/pages/Settings.jsx)).
- Integrates with the backend using a centralized Axios client ([client.js](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/frontend/src/api/client.js)) equipped with error response interceptors to handle session expiration redirects.

---

## 2. CodeQL Workflow Generation Feature Audit

The **CodeQL Provisioning Service** ([codeql_provisioner.py](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/services/github/codeql_provisioner.py)) automatically sets up static analysis on GitHub's hosted runners for newly installed repositories.

### Current Implementation Flow:
1. When the App is installed on a repository, the webhook triggers `_provision_codeql_for_repos`.
2. Checks if a CodeQL workflow already exists or if a setup PR is already open.
3. Creates a new branch `ai-risk-guard/codeql-setup`.
4. Pushes the static templates ([codeql.yml](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/templates/codeql/codeql.yml) and [codeql-config.yml](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/templates/codeql/codeql-config.yml)) using the GitHub contents PUT API.
5. Opens a Pull Request to merge the workflow into the default branch.

### Key Strengths:
- **Zero Compute Cost**: Offloads static analysis computation to GitHub-hosted runners.
- **Graceful Degradation**: Failures during provisioning are logged and swallowed, preventing installation hooks from failing.
- **Native Integration**: Alerts display natively in GitHub's Code Scanning dashboard alongside AI Risk Guard's custom SARIF reports.

---

## 3. High-Priority Production Issues & Vulnerabilities

The following bugs and architectural issues were identified during this audit.

### 🔴 1. Missing Database Migration for `codeql_provisioned` Column (Severity: Critical)
- **Location**: [utils/db.py:L26-L246](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/utils/db.py#L26-L246)
- **Description**: The database initializer `init_db()` is responsible for applying migrations. While it has blocks migrating the `user_id` and `display_name` columns, it does **not** check for or add the `codeql_provisioned` column to the `repos` table when it already exists on disk.
- **Impact**: Any installation webhook or PR scan attempting to upsert a repository or check its CodeQL status crashes with `sqlite3.OperationalError: table repos has no column named codeql_provisioned`. This is currently causing **6 E2E webhook tests to fail**.
- **Recommended Fix**: Add a migration check for `codeql_provisioned` inside `init_db()`:
  ```python
  cols = [row["name"] for row in conn.execute("PRAGMA table_info(repos)")]
  if "codeql_provisioned" not in cols:
      conn.execute("ALTER TABLE repos ADD COLUMN codeql_provisioned INTEGER DEFAULT 0")
  ```

### 🔴 2. Missing `/auth` Route Proxy in Dev Server (Severity: High)
- **Location**: [vite.config.js:L8-L13](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/frontend/vite.config.js#L8-L13)
- **Description**: The Vite developer server only proxies requests matching `/api` to the Flask backend running on port 8000. However, authentication endpoints like `/auth/login`, `/auth/callback`, and `/auth/logout` are not prefixed with `/api`.
- **Impact**: When testing the React frontend locally (port 3000), clicking "Login with GitHub" navigates the browser to `http://localhost:3000/auth/login`, resulting in a **404 Not Found** instead of initiating the OAuth flow.
- **Recommended Fix**: Add the `/auth` prefix to the Vite proxy rules:
  ```javascript
  proxy: {
    '/api': { target: 'http://localhost:8000', changeOrigin: true },
    '/auth': { target: 'http://localhost:8000', changeOrigin: true }
  }
  ```

### 🟡 3. Static Multi-Language CodeQL Matrix Overhead (Severity: Medium)
- **Location**: [codeql.yml:L22-L25](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/templates/codeql/codeql.yml#L22-L25)
- **Description**: The CodeQL workflow template uses a hardcoded language matrix: `language: [python, javascript]`.
- **Impact**: If the target repository only contains Python code (or only JavaScript code), the GitHub Actions runner will still spin up a secondary runner for the other language, leading to useless build logs and increased runner billing costs for the repository owner.
- **Recommended Fix**: Dynamically generate the language matrix payload inside `create_codeql_pr` based on the repository's detected language (available in the webhook payload) rather than using a static template.

### 🟡 4. Fallback Branch Assumption Bug for Non-`main` Repos (Severity: Medium)
- **Location**: [codeql_provisioner.py:L148-L201](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/services/github/codeql_provisioner.py#L148-L201)
- **Description**: In `github_webhook`, when `installation` or `installation_repositories` events are processed, they submit the repositories list to the provisioner. However, the GitHub webhook payload for these events does **not** include the `default_branch` attribute. The code falls back to `default_branch = repo.get("default_branch") or "main"`.
- **Impact**: If a repository's default branch is `master` or `develop`, the provisioner attempts to fetch `/git/ref/heads/main` which returns a `404`, silently skipping CodeQL setup.
- **Recommended Fix**: Query the GitHub Repository details API (`GET /repos/{owner}/{repo}`) inside the provisioner to fetch the true `default_branch` before creating the branch refs.

### 🟡 5. Lack of SHA on CodeQL Provisioner File Update (Severity: Medium)
- **Location**: [codeql_provisioner.py:L115-L130](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/services/github/codeql_provisioner.py#L115-L130)
- **Description**: When creating or updating the CodeQL workflow files on the branch, `_put_file` uses the `PUT /contents/{path}` API but does not pass a `sha` parameter.
- **Impact**: If the provisioning branch already exists and contains the CodeQL files (e.g., from an aborted setup run), the GitHub API will reject the PUT request with a `409 Conflict` (or `422`), causing the setup PR to fail.
- **Recommended Fix**: Attempt to retrieve the file metadata first. If the file exists, retrieve its `sha` and include it in the PUT request payload.

### 🟡 6. AST Cache Datatype Inconsistency (Severity: Low)
- **Location**: [db.py:L119](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/utils/db.py#L119) vs [ast_cache.py:L45](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/core/cache/ast_cache.py#L45)
- **Description**: `init_db()` creates the `ast_cache` table with `tree TEXT NOT NULL`, whereas `ASTCache._init_table()` creates it with `tree BLOB NOT NULL`.
- **Impact**: Storing binary pickled objects (`pickle.dumps(tree)`) in a `TEXT` column can lead to runtime encoding errors during retrieval in certain SQLite environments (due to implicit UTF-8 conversions).
- **Recommended Fix**: Update `utils/db.py` to declare the column as `BLOB NOT NULL`.

---

## 4. Key Architectural Improvements & Recommendations

In addition to fixing the production bugs above, the following improvements are recommended to elevate the platform:

1. **Token Auto-Refresh on Interceptor**: In [client.js](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/frontend/src/api/client.js#L8-L18), the Axios interceptor immediately redirects to `/login` on a `401`. Instead, it should first attempt to call a token refresh endpoint (or rely on Flask session cookie rehydration) to avoid interrupting the user's active session.
2. **Rate Limit Throttling Optimization**: If Gemini model fallbacks fail, [gemini_client.py](file:///C:/Users/Ralph/ME/Project/ai-risk-guard/core/llm/gemini_client.py#L70-L75) currently makes multiple blocking API calls to validate model IDs on *every* call to `generate`. The validation should be cached or locked once per session to avoid blocking analysis threads.
3. **Waitress Worker Scaling**: The server script starts Waitress with default single-thread settings. For higher concurrency loads in production, a reverse proxy (such as Nginx) should sit in front of the Flask app, and Waitress should be configured with multiple worker threads.
