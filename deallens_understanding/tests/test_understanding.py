"""Tests for the DealLens understanding primitive (no network, no API key)."""
import pytest

from understanding import invoke, manifest, understand
from understanding import llm


# A canned model reply used as an injected transport (stands in for the LLM).
def _mock_transport(prompt):
    assert "DOCUMENT:" in prompt          # prompt was assembled
    return {
        "financials": {"revenue": 20094200000, "net_income": 2593900000,
                       "depreciation": 546600000, "total_assets": 31452000000,
                       "total_liabilities": 20752000000, "bogus": "x"},
        "signals": {"top_customer_pct": 28, "owner_dependent": False,
                    "revenue_trend": "growing", "junk": 1},
        "findings": [
            {"category": "Customers", "finding": "Top retailer is 28% of sales.",
             "severity": "high"},
            {"category": "Legal", "finding": "Pending antitrust review.", "severity": "medium"},
            {"nonsense": True},           # dropped (no finding text)
        ],
    }


def _fence_transport(prompt):
    # Model wrapped its JSON in a ```json fence with prose around it.
    return llm.extract_json(
        'Here you go:\n```json\n{"financials": {"revenue": 100}, '
        '"signals": {}, "findings": []}\n```\nHope that helps!')


def _boom_transport(prompt):
    raise RuntimeError("429 rate limited")


DOC = ("General Mills Annual Report. Net sales 20,094.2. There is substantial doubt "
       "is NOT present. One customer, Walmart, represents a significant share. "
       "The company is party to litigation. Restructuring charges were recorded.")


# ---------------------------------------------------------------------------
# LLM path (injected transport)
# ---------------------------------------------------------------------------
def test_llm_path_shapes_output():
    r = understand({"text": DOC}, transport=_mock_transport)
    assert r["source"] == "llm"
    assert r["financials"]["revenue"] == 20094200000
    assert "bogus" not in r["financials"]          # non-field dropped
    assert r["signals"]["revenue_trend"] == "growing"
    assert "junk" not in r["signals"]
    assert len(r["findings"]) == 2                  # nonsense finding dropped
    assert r["findings"][0]["severity"] == "high"
    assert r["model"] == llm.model_name()


def test_llm_json_fence_parsing():
    r = understand({"text": DOC}, transport=_fence_transport)
    assert r["source"] == "llm"
    assert r["financials"]["revenue"] == 100.0


# ---------------------------------------------------------------------------
# Fallbacks
# ---------------------------------------------------------------------------
def test_llm_failure_falls_back_to_keywords():
    r = understand({"text": DOC}, transport=_boom_transport)
    assert r["source"] == "keywords_fallback"
    assert any("LLM call failed" in w for w in r["warnings"])
    # keyword scan still finds risk language
    assert any(f["category"] == "Legal" for f in r["findings"])


def test_keyword_path_when_no_llm(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = understand({"text": DOC})              # no transport, no key
    assert r["source"] == "keywords"
    cats = {f["category"] for f in r["findings"]}
    assert "Legal" in cats and "Customers" in cats
    assert any("No LLM configured" in w for w in r["warnings"])


def test_keyword_extracts_financials():
    r = understand({"text": "Total revenue 4,200,000\nNet income 520,000"})
    assert r["financials"]["revenue"] == 4_200_000
    assert r["financials"]["net_income"] == 520_000


# ---------------------------------------------------------------------------
# Primitive contract
# ---------------------------------------------------------------------------
def test_invoke_ok_envelope():
    env = invoke({"text": DOC}, transport=_mock_transport)
    assert env["ok"] is True and env["result"]["source"] == "llm"


def test_invoke_missing_text_errors():
    env = invoke({})
    assert env["ok"] is False and env["error"]["type"] == "ValueError"


def test_invoke_empty_text_errors():
    env = invoke({"text": "   "})
    assert env["ok"] is False


def test_manifest_reports_llm_flag(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    m = manifest()
    assert m["name"] == "deallens.understanding"
    assert m["uses_llm"] is False
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert manifest()["uses_llm"] is True


# ---------------------------------------------------------------------------
# llm helpers
# ---------------------------------------------------------------------------
def test_model_and_provider_defaults(monkeypatch):
    monkeypatch.delenv("DEALLENS_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("DEALLENS_LLM_MODEL", raising=False)
    assert llm.provider() == "anthropic"
    assert "claude" in llm.model_name()
    monkeypatch.setenv("DEALLENS_LLM_PROVIDER", "openai")
    assert "gpt" in llm.model_name()


def test_prompt_truncates_long_documents():
    huge = "x" * 200_000
    p = llm.build_prompt(huge)
    assert "truncated" in p and len(p) < 200_000


# ---------------------------------------------------------------------------
# Reporting-scale (the fix for the "quadrillion" bug): the model returns figures
# AS PRINTED plus a unit; we scale deterministically in code.
# ---------------------------------------------------------------------------
def test_reporting_scale_applied_in_millions():
    def t(prompt):
        return {"reporting_scale": "millions",
                "financials": {"revenue": 20094.2, "net_income": 2593.9,
                               "total_assets": 31452.0, "total_liabilities": 20752.0},
                "signals": {}, "findings": []}
    r = understand({"text": DOC}, transport=t)
    assert r["financials"]["revenue"] == 20094.2 * 1e6      # -> 20,094,200,000
    assert r["financials"]["net_income"] == 2593.9 * 1e6
    assert r["reporting_scale"] == "millions"
    assert any("scaled by 1,000,000" in w for w in r["warnings"])


def test_units_scale_leaves_absolute_numbers():
    def t(prompt):
        return {"reporting_scale": "units",
                "financials": {"revenue": 4200000, "net_income": 520000},
                "signals": {}, "findings": []}
    r = understand({"text": DOC}, transport=t)
    assert r["financials"]["revenue"] == 4_200_000


def test_implausible_figure_warns():
    def t(prompt):
        return {"reporting_scale": "millions",       # 20,094,200 (millions) -> 2.0e13
                "financials": {"revenue": 20094200.0}, "signals": {}, "findings": []}
    r = understand({"text": DOC}, transport=t)
    assert any("implausibly large" in w for w in r["warnings"])
