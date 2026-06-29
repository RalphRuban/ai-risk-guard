"""
Advanced GitHub PR security reporter.
"""
import requests
from utils.logger import logger
from core.reporting.explainer import SecurityExplainer
from core.metadata.vuln_metadata import VULN_METADATA
from core.patch.patch_generator import generate_patch

explainer = SecurityExplainer()


def build_summary(results):
    total = len(results)
    high = sum(1 for r in results if r["vulnerability"]["severity"] == "HIGH")
    medium = sum(1 for r in results if r["vulnerability"]["severity"] == "MEDIUM")
    low = sum(1 for r in results if r["vulnerability"]["severity"] == "LOW")

    return f"""
## 📊 Scan Summary
- Total Vulnerabilities: **{total}**
- High Severity: **{high}**
- Medium Severity: **{medium}**
- Low Severity: **{low}**
"""


def format_report(results):
    report = "# 🔐 AI Risk Guard Security Report\n"

    if not results:
        return report + "\n✅ No vulnerabilities detected.\n"

    report += build_summary(results)

    for result in results:
        vulnerability = result["vulnerability"]
        vulnerability_type = vulnerability["type"]
        explanation = explainer.remediation_summary(vulnerability)
        confidence = round(result.get("confidence", 0) * 100, 1)
        validation = result.get("validation", {})
        validation_status = "✅ Passed" if validation.get("success") else "❌ Failed"
        
        # Policy details (Week 3)
        policy_violations = validation.get("policy_violations", [])
        policy_status = "✅ Compliant" if not policy_violations else "⚠️ Non-Compliant"
        
        # Use relative path if available
        file_path = vulnerability.get("file_rel", vulnerability.get("file", "unknown"))

        # Industry mapping (CWE/OWASP)
        cwe_id = vulnerability.get("cwe", "N/A")
        owasp_id = vulnerability.get("owasp", "N/A")

        # Generate illustrative patch snippet
        suggested_patch = generate_patch(vulnerability)
        patch_snippet = suggested_patch.get("patch", "# No suggestion available.")

        report += f"""
---
### ⚠️ {vulnerability_type}
- **File**: `{file_path}` | **Line**: `{vulnerability.get("line")}`
- **Severity**: `{vulnerability.get("severity")}` | **Confidence**: `{confidence}%`
- **Risk Score**: `{result.get("risk")} / 10`
- **Validation**: `{validation_status}` | **Policy**: `{policy_status}`
- **Compliance**: `{cwe_id}` | `{owasp_id}`
"""
        
        if policy_violations:
            report += "#### 🚫 Policy Violations Detected\n"
            for violation in policy_violations:
                report += f"- {violation}\n"

        report += f"""
#### 💡 Impact & Resolution
- **Issue**: {explanation["issue"]}
- **Fix**: {explanation["fix"]}

#### 🧾 Suggested Secure Pattern
```python
{patch_snippet}
```

#### 🧾 Vulnerable Code
```python
{vulnerability.get("code")}
```

<details>
<summary><b>🔍 Technical Risk Breakdown</b></summary>

{format_breakdown(result.get("risk_breakdown", {}))}
</details>
"""
    
    # Add the combined diff at the end once
    if results and results[0].get("diff"):
        winner_id = results[0].get("candidate_id", "unknown")
        winner_source = results[0].get("candidate_source", "unknown")
        
        report += f"""
---
### 🛠️ Proposed Automated Patch
The system has selected the best available remediation candidate (**{winner_id}** via **{winner_source}**).

```diff
{results[0]["diff"]}
```
"""

    return report


def format_breakdown(breakdown):
    if not breakdown:
        return "No breakdown available."
    
    table = "| Factor | Score | Weight | Contribution |\n| :--- | :--- | :--- | :--- |\n"
    for factor, data in breakdown.items():
        table += f"| {factor.capitalize()} | {data['value']} | {data['weight']} | {data['contribution']} |\n"
    return table


def post_pr_comment(repository, pr_number, results, access_token):
    try:
        logger.info("Posting GitHub PR comment", "GITHUB")

        url = (
            f"https://api.github.com/repos/"
            f"{repository}/issues/"
            f"{pr_number}/comments"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }

        report = format_report(results)

        response = requests.post(
            url,
            json={"body": report},
            headers=headers,
            timeout=15,
        )

        if response.status_code in (200, 201):
            logger.info("PR comment posted successfully", "GITHUB")
        else:
            logger.error(
                f"GitHub API error: {response.status_code} {response.text[:200]}",
                "GITHUB",
            )

    except Exception as e:
        logger.error(f"GitHub reporter error: {e}", "GITHUB")