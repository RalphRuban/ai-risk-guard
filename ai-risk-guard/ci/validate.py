#!/usr/bin/env python3
"""
ci/validate.py — AI Risk Guard CI-runner validation harness (Phase E).

Runs the sandbox validation that the App could not perform locally (Docker
unavailable) on a GitHub-hosted Actions runner. The App dispatches pending
jobs via ``repository_dispatch``; this harness:

  fetch   — downloads each job payload from the App (secret-authenticated)
  run     — executes the real ``Sandbox`` against each payload, exactly as the
            App's Stage 2 (sandbox) + Stage 5 (regression tests) do
  report  — POSTs the runtime evidence back to the App, which re-injects it
            into a re-analysis pass so the PR comment/check are updated

The workflow that drives this lives in ``.github/workflows/ai-risk-guard-validate.yml``
in the workflow repo and must run from the repo root (it needs ``core/``, the
``sandbox/Dockerfile.sandbox`` and the sandbox config).

Usage (job IDs may be a JSON array string like "[1,2]" or space separated):
  python ci/validate.py fetch  --base-url URL --secret SECRET --job "[1,2]"
  python ci/validate.py run    --job "[1,2]"
  python ci/validate.py report --base-url URL --secret SECRET --job "[1,2]"
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

import requests

WORK_DIR = Path("ci-work")
JOB_IDS_ENV = "CI_VALIDATION_JOB_IDS"

_RUNTIME_VER = "1"
_SCHEMA_VERSION = 1


def _auth_headers(secret: str) -> dict:
    return {"X-CI-Validation-Secret": secret}


def _parse_job_ids(raw: str) -> list[int]:
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [int(x) for x in parsed]
        return [int(parsed)]
    except (ValueError, TypeError):
        ids = []
        for token in raw.replace(",", " ").split():
            try:
                ids.append(int(token))
            except ValueError:
                continue
        return ids


def _job_workdir(job_id: int) -> Path:
    d = WORK_DIR / f"job-{job_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def fetch(base_url: str, secret: str, job_ids: list[int]) -> int:
    if not base_url or not secret:
        raise SystemExit("fetch requires --base-url and --secret")
    fetched = 0
    for job_id in job_ids:
        url = f"{base_url}/api/ci-validation/jobs/{job_id}"
        resp = requests.get(url, headers=_auth_headers(secret), timeout=60)
        if resp.status_code != 200:
            print(f"[ci/validate] job {job_id}: fetch failed ({resp.status_code}): {resp.text[:300]}", file=sys.stderr)
            continue
        payload = resp.json()
        payload["_schema_version"] = _SCHEMA_VERSION
        out = _job_workdir(job_id) / "payload.json"
        out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        fetched += 1
    print(f"[ci/validate] fetched {fetched}/{len(job_ids)} payloads")
    return fetched


def run(job_ids: list[int]) -> int:
    from core.validator.sandbox import Sandbox

    ran = 0
    for job_id in job_ids:
        workdir = _job_workdir(job_id)
        payload_path = workdir / "payload.json"
        if not payload_path.exists():
            print(f"[ci/validate] job {job_id}: no payload — skipping", file=sys.stderr)
            continue
        payload = json.loads(payload_path.read_text(encoding="utf-8"))

        patched_code = payload.get("patched_code") or ""
        source_filename = payload.get("source_filename") or "main.py"
        test_content = payload.get("test_content") or ""
        test_filename = payload.get("test_filename") or "test_validation.py"
        extra_files = payload.get("extra_files") or []
        scan_mode = payload.get("scan_mode") or None
        network = payload.get("sandbox_network") or None

        result: dict[str, Any] = {"sandbox": None, "test_results": None, "error": None}
        try:
            sandbox = Sandbox()

            # Mirror the App's Stage 2: sandbox execution of the patched code.
            test_path = None
            if test_content:
                test_path = str(workdir / test_filename)
                Path(test_path).parent.mkdir(parents=True, exist_ok=True)
                Path(test_path).write_text(test_content, encoding="utf-8")

            result["sandbox"] = sandbox.run(
                patched_code,
                test_file_path=test_path,
                source_filename=source_filename,
                scan_mode=scan_mode,
                network=network,
            )

            # Mirror the App's Stage 5: synthesized regression tests.
            result["test_results"] = {
                "success": False,
                "skipped": True,
                "output": "",
                "error": "No test file",
            }
            if test_path:
                result["test_results"] = sandbox.run_tests(
                    test_path,
                    source_code=patched_code,
                    source_filename=source_filename,
                    extra_files=extra_files,
                    scan_mode=scan_mode,
                    network=network,
                )

            result["runner"] = "github_actions"
            result["_runtime_version"] = _RUNTIME_VER
        except Exception as exc:  # always report something
            result["error"] = f"{type(exc).__name__}: {exc}"

        (workdir / "result.json").write_text(
            json.dumps(result, ensure_ascii=False), encoding="utf-8"
        )
        ran += 1
        print(f"[ci/validate] job {job_id}: sandbox={result['sandbox'] and result['sandbox'].get('success')} tests={result['test_results'] and (result['test_results'].get('success'), result['test_results'].get('skipped'))}")
    return ran


def report(base_url: str, secret: str, job_ids: list[int]) -> int:
    if not base_url or not secret:
        raise SystemExit("report requires --base-url and --secret")
    reported = 0
    for job_id in job_ids:
        workdir = _job_workdir(job_id)
        result_path = workdir / "result.json"
        if not result_path.exists():
            print(f"[ci/validate] job {job_id}: no result — skipping", file=sys.stderr)
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        status = "completed" if result.get("error") is None else "failed"
        body = {
            "job_id": job_id,
            "status": status,
            "sandbox_res": result.get("sandbox") or {},
            "test_results": result.get("test_results") or {},
        }
        if result.get("error"):
            body["error"] = result["error"]
        url = f"{base_url}/api/ci-validation/results"
        resp = requests.post(url, json=body, headers=_auth_headers(secret), timeout=60)
        if resp.status_code not in (200, 201, 204):
            print(f"[ci/validate] job {job_id}: report failed ({resp.status_code}): {resp.text[:300]}", file=sys.stderr)
            continue
        reported += 1
    print(f"[ci/validate] reported {reported}/{len(job_ids)} results")
    return reported


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI Risk Guard CI validation harness")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, handler in (("fetch", fetch), ("report", report)):
        p = sub.add_parser(name)
        p.add_argument("--base-url", required=True)
        p.add_argument("--secret", required=True)
        p.add_argument("--job", default=os.getenv(JOB_IDS_ENV, ""))
        p.set_defaults(_handler=handler)

    p = sub.add_parser("run")
    p.add_argument("--job", default=os.getenv(JOB_IDS_ENV, ""))
    p.set_defaults(_handler=run)

    args = parser.parse_args(argv)
    job_ids = _parse_job_ids(args.job)
    if not job_ids:
        raise SystemExit("no job ids provided via --job")
    if args.command in ("fetch", "report"):
        args._handler(args.base_url, args.secret, job_ids)
    else:
        args._handler(job_ids)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
