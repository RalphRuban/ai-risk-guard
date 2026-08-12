"""Tests for the LLM-backed analysis refinements (triage, explanations, summary)."""

import os
from unittest.mock import MagicMock, patch

from core.config import config
from core.triage.llm_triage import LLMTriage

_VALID_CANDIDATE = {
    "id": "cand_1",
    "source": "ast",
    "code": 'import subprocess\nsubprocess.run(["ls"], shell=False)',
    "validation_score": 0.85,
    "validation_details": {
        "syntax": {"success": True},
        "sandbox": {"success": True},
        "rescan": {"success": True, "remaining_vulnerabilities": []},
        "policy": {"success": True},
    },
    "test_results": {"success": True},
    "quality_score": 0.8,
    "quality_breakdown": {},
}

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(response=None, enabled=True, side_effect=None):
    client = MagicMock()
    client.enabled = enabled
    if side_effect is not None:
        client.cached_generate.side_effect = side_effect
    else:
        client.cached_generate.return_value = response
    return client


def _make_triage(client):
    with patch("core.triage.llm_triage.GeminiClient", return_value=client):
        triage = LLMTriage()
    return triage


def _vuln(vtype, line=1, code="x", detection_confidence=None):
    vuln = {"type": vtype, "line": line, "code": code, "message": "msg"}
    if detection_confidence is not None:
        vuln["detection_confidence"] = detection_confidence
    return vuln


# ---------------------------------------------------------------------------
# Verdict parsing
# ---------------------------------------------------------------------------


def test_parse_verdicts():
    verdicts, reasons = LLMTriage._parse_verdicts(
        "0: REJECTED: constant value, not reachable\n"
        "1. CONFIRMED: real exploit\n"
        "garbage line\n"
        "2) UNCERTAIN: unclear\n"
        "9: CONFIRMED: out of range",
        3,
    )
    assert verdicts == {0: "REJECTED", 1: "CONFIRMED", 2: "UNCERTAIN"}
    assert reasons[0] == "constant value, not reachable"
    assert reasons[1] == "real exploit"
    assert 9 not in verdicts


def test_parse_verdicts_is_case_insensitive():
    verdicts, _ = LLMTriage._parse_verdicts("0: rejected: nope", 1)
    assert verdicts == {0: "REJECTED"}


# ---------------------------------------------------------------------------
# Candidate selection
# ---------------------------------------------------------------------------


def test_triage_candidates_filters_by_confidence_threshold():
    client = _make_client()
    triage = _make_triage(client)
    high = _vuln("COMMAND_INJECTION", detection_confidence=0.98)
    low = _vuln("SQL_INJECTION", detection_confidence=0.90)
    with patch.object(config.app.triage, "min_detection_confidence", 0.95):
        candidates = triage._triage_candidates([high, low])
    assert len(candidates) == 1
    assert candidates[0] is low


def test_triage_candidates_excludes_silent_types():
    client = _make_client()
    triage = _make_triage(client)
    silent = _vuln("DEBUG_CODE", detection_confidence=0.90)
    with patch.object(config.app.triage, "min_detection_confidence", 1.0):
        candidates = triage._triage_candidates([silent])
    assert candidates == []


def test_detection_confidence_falls_back_to_type_table():
    client = _make_client()
    triage = _make_triage(client)
    assert triage._detection_confidence(_vuln("SQL_INJECTION")) == 0.90
    assert triage._detection_confidence(_vuln("UNKNOWN_TYPE")) == 0.9


# ---------------------------------------------------------------------------
# Triage flow
# ---------------------------------------------------------------------------


def test_triage_disabled_returns_input_unchanged():
    client = _make_client("0: REJECTED: no")
    triage = _make_triage(client)
    vulns = [_vuln("COMMAND_INJECTION", detection_confidence=0.90)]
    with patch.object(config.app.triage, "enabled", False):
        result = triage.triage_vulnerabilities(vulns)
    assert result is vulns
    client.cached_generate.assert_not_called()


def test_triage_skips_api_when_client_disabled():
    client = _make_client(enabled=False)
    triage = _make_triage(client)
    vulns = [_vuln("COMMAND_INJECTION", detection_confidence=0.90)]
    with patch.object(config.app.triage, "enabled", True):
        result = triage.triage_vulnerabilities(vulns)
    assert result is vulns
    client.cached_generate.assert_not_called()


def test_triage_skips_api_when_no_candidates():
    client = _make_client()
    triage = _make_triage(client)
    vulns = [_vuln("COMMAND_INJECTION", detection_confidence=0.98)]
    with patch.object(config.app.triage, "enabled", True), patch.object(
        config.app.triage, "min_detection_confidence", 0.95
    ):
        result = triage.triage_vulnerabilities(vulns)
    assert result is vulns
    client.cached_generate.assert_not_called()


def test_triage_applies_rejected_and_confirmed_verdicts():
    client = _make_client("0: REJECTED: constant, not reachable\n1: CONFIRMED: real\n")
    triage = _make_triage(client)
    vulns = [
        _vuln("COMMAND_INJECTION", detection_confidence=0.90),
        _vuln("SQL_INJECTION", detection_confidence=0.90),
    ]
    with patch.object(config.app.triage, "enabled", True), patch.object(
        config.app.triage, "min_detection_confidence", 1.0
    ):
        result = triage.triage_vulnerabilities(vulns)
    assert result[0]["unconfirmed"] is True
    assert result[0]["triage"] == {"verdict": "rejected", "reason": "constant, not reachable"}
    assert "unconfirmed" not in result[1]
    assert result[1]["triage"]["verdict"] == "confirmed"
    client.cached_generate.assert_called_once()


def test_triage_defaults_missing_verdicts_to_uncertain():
    client = _make_client("0: REJECTED: nope\n")  # index 1 missing
    triage = _make_triage(client)
    vulns = [
        _vuln("COMMAND_INJECTION", detection_confidence=0.90),
        _vuln("SQL_INJECTION", detection_confidence=0.90),
    ]
    with patch.object(config.app.triage, "enabled", True), patch.object(
        config.app.triage, "min_detection_confidence", 1.0
    ):
        result = triage.triage_vulnerabilities(vulns)
    assert result[0]["unconfirmed"] is True
    assert result[1]["triage"]["verdict"] == "uncertain"
    assert "unconfirmed" not in result[1]


def test_triage_fails_open_when_llm_unavailable():
    client = _make_client(None)
    triage = _make_triage(client)
    vulns = [_vuln("COMMAND_INJECTION", detection_confidence=0.90)]
    with patch.object(config.app.triage, "enabled", True), patch.object(
        config.app.triage, "min_detection_confidence", 1.0
    ):
        result = triage.triage_vulnerabilities(vulns)
    assert result is vulns
    assert "triage" not in result[0]
    assert "unconfirmed" not in result[0]


# ---------------------------------------------------------------------------
# Explanations
# ---------------------------------------------------------------------------


def test_explanations_disabled_returns_empty():
    client = _make_client("0. text")
    triage = _make_triage(client)
    with patch.object(config.app.explainer, "enabled", False):
        out = triage.generate_explanations([_vuln("COMMAND_INJECTION")], "x")
    assert out == {}
    client.cached_generate.assert_not_called()


def test_explanations_parses_numbered_lines():
    client = _make_client(
        "0. Runs a command built from user input, allowing shell injection. "
        "Use subprocess.run with shell=False.\n"
    )
    triage = _make_triage(client)
    with patch.object(config.app.explainer, "enabled", True):
        out = triage.generate_explanations(
            [_vuln("COMMAND_INJECTION", code="subprocess.run(cmd, shell=True)")], "x"
        )
    assert 0 in out
    assert "shell=False" in out[0]


def test_explanations_fail_open_on_none_response():
    client = _make_client(None)
    triage = _make_triage(client)
    with patch.object(config.app.explainer, "enabled", True):
        out = triage.generate_explanations([_vuln("COMMAND_INJECTION")], "x")
    assert out == {}


def test_explanations_empty_findings_returns_empty():
    client = _make_client("0. text")
    triage = _make_triage(client)
    with patch.object(config.app.explainer, "enabled", True):
        out = triage.generate_explanations([], "x")
    assert out == {}
    client.cached_generate.assert_not_called()


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def test_summary_disabled_returns_none():
    client = _make_client("text")
    triage = _make_triage(client)
    with patch.object(config.app.summary, "enabled", False):
        out = triage.summarize_analysis([{"vulnerability": {"type": "X", "line": 1}, "risk": 3.5}])
    assert out is None
    client.cached_generate.assert_not_called()


def test_summary_returns_text():
    client = _make_client("Two command-injection findings were patched; one was suppressed.")
    triage = _make_triage(client)
    with patch.object(config.app.summary, "enabled", True):
        out = triage.summarize_analysis(
            [{"vulnerability": {"type": "COMMAND_INJECTION", "file_rel": "a.py", "line": 3}, "risk": 7.5}]
        )
    assert out == "Two command-injection findings were patched; one was suppressed."


def test_summary_empty_findings_returns_none():
    client = _make_client("text")
    triage = _make_triage(client)
    with patch.object(config.app.summary, "enabled", True):
        out = triage.summarize_analysis([])
    assert out is None
    client.cached_generate.assert_not_called()


def test_summary_fail_open_on_none_response():
    client = _make_client(None)
    triage = _make_triage(client)
    with patch.object(config.app.summary, "enabled", True):
        out = triage.summarize_analysis([{"vulnerability": {"type": "X"}, "risk": 1.0}])
    assert out is None


# ---------------------------------------------------------------------------
# RiskAgent integration
# ---------------------------------------------------------------------------


def _risk_context(vulns, llm_triage=None):
    return {
        "vulnerabilities": vulns,
        "patch_candidates": [_VALID_CANDIDATE],
        "file_path": __file__,
        "repo_root": _REPO_ROOT,
        "pr_context": {},
        "llm_triage": llm_triage,
    }


def test_risk_agent_marks_unconfirmed_vuln_non_gating():
    from core.agents.risk_agent import RiskAgent
    agent = RiskAgent()
    result = agent.execute(
        _risk_context([{"type": "COMMAND_INJECTION", "severity": "HIGH", "file": "test.py", "unconfirmed": True}])
    )
    r = result["results"][0]
    assert r["unconfirmed"] is True
    assert r["is_silent"] is True


def test_risk_agent_confirmed_vuln_promotes_detection_confidence():
    from core.agents.risk_agent import RiskAgent
    agent = RiskAgent()
    result = agent.execute(
        _risk_context(
            [
                {
                    "type": "SQL_INJECTION",
                    "severity": "HIGH",
                    "file": "test.py",
                    "triage": {"verdict": "confirmed", "reason": "real exploit"},
                }
            ]
        )
    )
    r = result["results"][0]
    assert r["detection_confidence"] == 0.98
    assert r["triage"]["verdict"] == "confirmed"


def test_risk_agent_attaches_llm_rationale():
    from core.agents.risk_agent import RiskAgent
    fake_triage = MagicMock()
    fake_triage.generate_explanations.return_value = {0: "AI-generated explanation"}
    agent = RiskAgent()
    result = agent.execute(
        _risk_context(
            [{"type": "COMMAND_INJECTION", "severity": "HIGH", "file": "test.py"}],
            llm_triage=fake_triage,
        )
    )
    assert result["results"][0]["llm_rationale"] == "AI-generated explanation"


# ---------------------------------------------------------------------------
# Reporter rendering
# ---------------------------------------------------------------------------


def test_format_report_renders_llm_summary():
    from services.github.reporter import format_report
    report = format_report([], llm_summary="Two issues patched.")
    assert "**Summary**: Two issues patched." in report


def test_format_report_omits_summary_when_none():
    from services.github.reporter import format_report
    report = format_report([])
    assert "Summary" not in report


def test_finding_card_prefers_llm_rationale():
    from services.github.reporter import _format_finding_card
    r = {
        "vulnerability": {"type": "COMMAND_INJECTION", "severity": "HIGH", "file_rel": "a.py", "line": 3},
        "risk": 8.0,
        "confidence": 0.9,
        "priority": "HIGH",
        "detection_confidence": 0.95,
        "is_silent": False,
        "unconfirmed": False,
        "patch": "",
        "diff": "",
        "llm_rationale": "AI rationale",
        "risk_rationale": "static rationale",
        "evidence": {"rule": ""},
        "validation": {},
    }
    card = _format_finding_card(r)
    assert "AI rationale" in card
    assert "static rationale" not in card


def test_finding_card_shows_unconfirmed_tag():
    from services.github.reporter import _format_finding_card
    r = {
        "vulnerability": {"type": "COMMAND_INJECTION", "severity": "HIGH", "file_rel": "a.py", "line": 3},
        "risk": 8.0,
        "confidence": 0.9,
        "priority": "HIGH",
        "detection_confidence": 0.95,
        "is_silent": True,
        "unconfirmed": True,
        "patch": "",
        "diff": "",
        "risk_rationale": "",
        "evidence": {"rule": ""},
        "validation": {},
    }
    card = _format_finding_card(r)
    assert "unconfirmed by AI review" in card
