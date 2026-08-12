"""
Validator Agent.
Responsible for verifying the integrity and security of applied patches.
Runs synthesized regression tests and computes quality scores.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from core.agents.base_agent import BaseAgent
from core.config import config
from core.exceptions import InputValidationError, ValidationError
from core.policy.policy_engine import PolicyEngine
from core.quality.patch_scorer import PatchScorer
from core.utils.validation import validate_code_input
from core.validator.patch_validator import PatchValidator
from core.validator.sandbox import Sandbox
from core.validator.security_rescan import SecurityRescanner

log = logging.getLogger("ai_risk_guard.validator_agent")

_SSRF_TEST_URLS = [
    ("https://example.com", False),
    ("http://example.com:8080/path?q=1", False),
    ("http://8.8.8.8", False),
    ("http://1.1.1.1", False),
    ("http://127.0.0.1", True),
    ("http://127.0.0.1:8080/admin", True),
    ("http://localhost", True),
    ("http://localhost:3000", True),
    ("http://[::1]", True),
    ("http://10.0.0.1", True),
    ("http://10.0.0.1:5432", True),
    ("http://172.16.0.1", True),
    ("http://172.31.255.255", True),
    ("http://192.168.1.1", True),
    ("http://169.254.169.254", True),
    ("http://100.64.0.1", True),
    ("http://[fd00::1]", True),
    ("http://[fe80::1]", True),
    ("http://0.0.0.0", True),
    ("file:///etc/passwd", True),
    ("ftp://attacker.com", True),
    ("", True),
]


def _check_ssrf_patch(patched_code: str) -> dict[str, Any]:
    """Test validate_url_ssrf() against a URL matrix to verify blocking behavior."""
    if "validate_url_ssrf" not in patched_code:
        return {"success": None, "skipped": True}

    try:
        from core.patch.fixers import _SSRF_VALIDATOR_SRC
        ns: dict[str, Any] = {}
        exec(_SSRF_VALIDATOR_SRC, ns)
        validator = ns["validate_url_ssrf"]
    except Exception as e:
        return {"success": False, "error": f"Failed to load validator: {e}"}

    failures = []
    for url, should_block in _SSRF_TEST_URLS:
        try:
            validator(url)
            if should_block:
                failures.append(f"{url!r} should have been blocked")
        except ValueError:
            if not should_block:
                failures.append(f"{url!r} should have been allowed")
        except Exception as e:
            failures.append(f"{url!r} raised {e}")

    if failures:
        return {
            "success": False,
            "error": "; ".join(failures),
            "total": len(_SSRF_TEST_URLS),
            "failed": len(failures),
        }

    return {"success": True, "total": len(_SSRF_TEST_URLS), "failed": 0}


class ValidatorAgent(BaseAgent):
    """
    Agent specialized in patch verification and security re-scanning.
    Now includes Policy Enforcement, Test-Aware validation, and quality scoring.
    """
    
    def __init__(self):
        super().__init__("Validator")
        self.validator = PatchValidator()
        self.rescanner = SecurityRescanner()
        self.sandbox = Sandbox()
        self.policy_engine = PolicyEngine()
        self.patch_scorer = PatchScorer()

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        candidates = context.get("patch_candidates", [])
        test_file = context.get("test_file_path") or context.get("associated_test_file")
        repo_root = context.get("repo_root", "")
        file_path = context.get("file_path", "")
        source_filename = os.path.relpath(file_path, repo_root).replace("\\", "/") if repo_root and file_path else os.path.basename(file_path) or None
        
        if not candidates:
            self.log("No patch candidates to validate")
            return context

        self.log(f"Starting multi-stage validation for {len(candidates)} candidates")
        if test_file:
            self.log(f"Running synthesized tests from: {os.path.basename(test_file)}")
        
        def _validate_one(candidate):
            try:
                patched_code = candidate.get("code")
                if not patched_code:
                    self.log(f"Candidate {candidate.get('id', 'unknown')} has no code, skipping", "warning")
                    return candidate

                validate_code_input(patched_code)
                self.log(f"Validating candidate: {candidate['id']} ({candidate['source']})")

                ssrf_res = {"skipped": True}

                # Stage 0: Enforce mandatory sanitizers
                patched_code = self.policy_engine.enforce_sanitizers(patched_code)
                candidate["code"] = patched_code

                # Per-user scan configuration (Phase 4.1). Resolved once per
                # scan by the webhook and threaded via pr_context.
                scan_settings = (context.get("pr_context") or {}).get("scan_settings") or {}
                scan_mode = scan_settings.get("scan_mode")
                network = scan_settings.get("sandbox_network")

                # Stage 1: Syntax & Semantic Checks
                syntax_res = self.validator.validate_all(patched_code)

                # Stage 2: Sandbox Execution (per-thread sandbox instance for thread safety)
                thread_sandbox = Sandbox()
                sandbox_res = thread_sandbox.run(
                    patched_code,
                    test_file_path=test_file,
                    source_filename=source_filename,
                    scan_mode=scan_mode,
                    network=network,
                )
                
                # Stage 2.5: SSRF Validator Check
                ssrf_res = _check_ssrf_patch(patched_code)
                if ssrf_res.get("success") is False:
                    sandbox_res["success"] = False
                    existing_error = sandbox_res.get("error") or ""
                    sandbox_res["error"] = f"{existing_error} SSRF validator check failed".strip()
                    self.log(f"SSRF validator check FAILED for candidate {candidate['id']}: {ssrf_res['error']}", "warning")
                
                # Stage 3: Security Re-scan
                rescan_res = self.rescanner.rescan_code(patched_code)
                
                # Stage 4: Policy Enforcement
                policy_res = self.policy_engine.check_compliance(patched_code)
                
                # Stage 5: Run synthesized regression tests
                test_results = {"success": False, "skipped": True, "output": "", "error": "No test file"}
                if test_file and os.path.exists(test_file):
                    extra_files = context.get("test_deps") or []
                    test_results = thread_sandbox.run_tests(
                        test_file, source_code=patched_code, source_filename=source_filename, extra_files=extra_files,
                        scan_mode=scan_mode, network=network,
                    )
                    if not test_results.get("skipped"):
                        test_results["skipped"] = False

                    if test_results.get("mode") == "local":
                        test_results["docker_unavailable"] = True

                    docker_ran = (
                        test_results.get("mode") == "docker"
                        and thread_sandbox._is_docker_available()
                    )
                    # In explicit comparison mode, always capture local results so
                    # the PR comment can show a Docker-vs-Local comparison even when
                    # the Docker engine is unavailable (mode == "local").
                    want_comparison = (
                        scan_mode == "sandbox_and_local_comparison"
                        and not test_results.get("skipped")
                    )
                    want_fallback_comparison = (
                        config.sandbox.enable_local_fallback_comparison
                        and docker_ran
                        and not test_results.get("skipped")
                        and test_results.get("success") is False
                    )
                    if want_comparison or want_fallback_comparison:
                        try:
                            local_results = thread_sandbox._run_local_tests(
                                test_file, source_code=patched_code, source_filename=source_filename, extra_files=extra_files
                            )
                            # Local results must get the same expected-failure
                            # attribution as the Docker result, otherwise the
                            # same pinned-vulnerability tests show as "Docker
                            # passed / Local failed" in the comparison table.
                            if (
                                config.sandbox.enable_expected_failure_analysis
                                and not local_results.get("skipped")
                                and local_results.get("output")
                            ):
                                self._classify_expected_failures(local_results, candidate, context, test_file)
                            test_results["local_fallback"] = {
                                "success": local_results.get("success"),
                                "raw_success": local_results.get(
                                    "raw_success", local_results.get("success")
                                ),
                                "mode": local_results.get("mode"),
                                "expected_failures": local_results.get("expected_failures", []),
                                "regression_failures": local_results.get("regression_failures", []),
                                "passing_tests": local_results.get("passing_tests", []),
                            }
                            self.log(
                                f"Local comparison: "
                                f"{'PASS' if local_results.get('success') else 'FAIL'} "
                                f"({len(local_results.get('expected_failures', []))} expected, "
                                f"{len(local_results.get('regression_failures', []))} regressions)"
                            )
                        except Exception as e:
                            self.log(f"Local fallback comparison failed: {e}", "warning")

                    if (
                        config.sandbox.enable_expected_failure_analysis
                        and not test_results.get("skipped")
                        and test_results.get("success") is False
                        and test_results.get("output")
                    ):
                        self._classify_expected_failures(test_results, candidate, context, test_file)

                    if test_results.get("success"):
                        self.log(f"Regression tests PASSED for candidate {candidate['id']}")
                    else:
                        self.log(f"Regression tests FAILED for candidate {candidate['id']}", "warning")
                
                score = 0.0
                if syntax_res.get("success") is True: score += 0.20
                if sandbox_res.get("success") is True: score += 0.25
                if rescan_res.get("success") is True: score += 0.15
                if policy_res.get("success") is True: score += 0.15

                if test_results.get("success") is True:
                    test_mode = test_results.get("mode", "unknown")
                    if test_mode == "docker":
                        score += 0.25
                    elif test_mode == "local":
                        score += 0.15
                    else:
                        score += 0.10
                elif test_results.get("skipped") is True:
                    score += 0.10

                score = round(score, 2)
                
                candidate["validation_score"] = score
                candidate["validation_details"] = {
                    "syntax": syntax_res, "sandbox": sandbox_res,
                    "rescan": rescan_res, "policy": policy_res,
                    "ssrf_validator": ssrf_res,
                }
                candidate["test_results"] = test_results
                candidate["quality_score"] = self.patch_scorer.score(candidate, context)
                try:
                    from app.metrics import patch_quality
                    patch_quality.observe(candidate["quality_score"])
                except ImportError:
                    pass

                if score >= 1.0:
                    self.log(f"Candidate {candidate['id']} PASSED all stages (Quality: {candidate['quality_score']})")
                else:
                    self.log(f"Candidate {candidate['id']} FAILED (Score: {score})", "warning")
                    if not syntax_res.get("success"):
                        self.log(f"  - Syntax failure: {syntax_res.get('stage')}", "debug")
                    if not sandbox_res.get("success"):
                        self.log(f"  - Sandbox: {sandbox_res.get('error')}", "debug")
                    if not rescan_res.get("success"):
                        self.log(f"  - Rescan: {len(rescan_res.get('remaining_vulnerabilities', []))} left", "debug")
                    if not policy_res.get("success"):
                        self.log(f"  - Policy: {policy_res.get('violations')}", "debug")
                    if not test_results.get("success"):
                        combined = " | ".join(filter(None, [
                            test_results.get("error", ""),
                            test_results.get("output", ""),
                        ]))
                        self.log(f"  - Tests: {combined or 'failed'}", "debug")
            except InputValidationError as e:
                self.log(f"Input validation failed for {candidate.get('id', 'unknown')}: {e}", "error")
                candidate["validation_score"] = 0.0
                candidate["validation_details"] = {"error": "Input validation failed"}
            except ValidationError as e:
                self.log(f"Validation failed for {candidate.get('id', 'unknown')}: {e}", "error")
                candidate["validation_score"] = 0.0
                candidate["validation_details"] = {"error": "Validation failed"}
            except Exception as e:
                self.log(f"Unexpected error for {candidate.get('id', 'unknown')}: {e}", "error")
                log.exception("Unexpected validation error")
                candidate["validation_score"] = 0.0
                candidate["validation_details"] = {"error": "Unexpected validation error"}
            return candidate

        max_workers = min(len(candidates), 3)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_validate_one, c): c for c in candidates}
            for future in as_completed(futures):
                future.result()

        return context

    def _classify_expected_failures(
        self,
        test_results: dict[str, Any],
        candidate: dict[str, Any],
        context: dict[str, Any],
        test_file: str | None,
    ) -> None:
        """Attribute failing regression tests to the removed vulnerabilities.

        A test that references a symbol the patch changed pins the pre-fix
        behavior and is expected to fail — it is not a regression.
        """
        try:
            from core.validator.expected_test_failures import analyze_test_results

            original = context.get("original_code") or ""
            patched = candidate.get("code") or ""
            test_source = ""
            if test_file and os.path.exists(test_file):
                with open(test_file, "r", encoding="utf-8", errors="ignore") as f:
                    test_source = f.read()

            analysis = analyze_test_results(
                original, patched, test_source, test_results.get("output") or ""
            )
            test_results["expected_failures"] = analysis["expected_failures"]
            test_results["regression_failures"] = analysis["regression_failures"]
            test_results["passing_tests"] = analysis["passing_tests"]

            if analysis["regression_failures"]:
                self.log(
                    f"{analysis['regressions']} regression(s) remain: "
                    f"{', '.join(analysis['regression_failures'])}",
                    "warning",
                )
            else:
                test_results["raw_success"] = test_results.get("success")
                test_results["success"] = True
                self.log(
                    f"No true regressions — {analysis['expected']} failing test(s) pin removed vulnerabilities: "
                    f"{', '.join(analysis['expected_failures'])}",
                )
        except Exception as e:
            self.log(f"Expected-failure analysis failed: {e}", "warning")
