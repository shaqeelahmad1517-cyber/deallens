"""Tests for the DealLens report primitive."""
import pytest

from report import build_html, build_markdown, extract, invoke, render

# A minimal bare valuation result.
VAL_RESULT = {
    "target_name": "Acme Co",
    "normalization": {"normalized_ebitda": 830000.0, "sde": 1010000.0, "revenue": 4200000},
    "effective_discount_rate": 0.26,
    "risk": {"multiple_discount": 0.24, "flags": [
        {"label": "Customer concentration", "severity": "high", "category": "Customers"}]},
    "approaches": {
        "income": {"dcf": {"value": 2589041.77}, "capitalization": {"value": 3458333.33},
                   "range": {"low": 2589041.77, "high": 3458333.33}},
        "market": {"metric": "sde", "low_multiple": 2.49, "high_multiple": 4.15,
                   "low": 2514900.0, "high": 4191500.0},
        "asset": {"value": 1250000},
    },
    "triangulation": {"weighted_range": {"low": 1921022, "high": 2618932, "mid": 2269977}},
    "sensitivity": {"discount_rate": [
        {"discount_rate": 0.25, "dcf_value": 2700000},
        {"discount_rate": 0.26, "dcf_value": 2589041},
    ]},
    "recommended_range": {"low": 1921022, "high": 2618932, "mid": 2269977},
    "disclaimer": "Decision-support only.",
}

# A minimal orchestrator-shaped result.
ORCH_RESULT = {
    "target_name": "Acme Co",
    "recommendation": {"range": {"low": 1921022, "high": 2618932, "mid": 2269977}},
    "diligence": {
        "completion_pct": 25.9,
        "summary": {"overall_risk_level": "medium", "red_flag_count": 2},
        "red_flags": [
            {"label": "Customer concentration: top customer = 38%", "severity": "high", "category": "Customers"},
            {"label": "Owner dependence", "severity": "high", "category": "People"},
        ],
        "risk_profile": [],
    },
    "comparables": {
        "sector_matched": "logistics", "metric": "sde", "base_band": [2.0, 3.0],
        "low_multiple": 2.14, "high_multiple": 3.21,
        "modifiers": {"size_factor": 1.0, "growth_factor": 1.07}, "source": "Illustrative",
    },
    "valuation": VAL_RESULT,
    "disclaimer": "Decision-support only.",
}


# ---------------------------------------------------------------------------
# Shape normalization
# ---------------------------------------------------------------------------
def test_extract_from_valuation():
    d = extract(VAL_RESULT)
    assert d["target_name"] == "Acme Co"
    assert d["recommended_range"]["mid"] == 2269977


def test_extract_from_orchestrator():
    d = extract(ORCH_RESULT)
    assert d["comparables"]["sector_matched"] == "logistics"
    assert len(d["red_flags"]) == 2
    assert d["diligence"]["completion_pct"] == 25.9


def test_extract_rejects_garbage():
    with pytest.raises(ValueError):
        extract({"nope": 1})


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------
def test_html_contains_key_facts():
    h = build_html(ORCH_RESULT, {"as_of": "June 2026"})
    assert "Acme Co" in h
    assert "$1,921,022" in h and "$2,618,932" in h
    assert "logistics" in h
    assert "Customer concentration" in h
    assert h.strip().startswith("<!DOCTYPE html>")


def test_markdown_contains_sections():
    m = build_markdown(ORCH_RESULT)
    assert "# Valuation Report — Acme Co" in m
    assert "## Recommended Value Range" in m
    assert "## Valuation Approaches" in m
    assert "Owner dependence" in m


def test_render_valuation_only_has_no_comparables_section():
    h = build_html(VAL_RESULT)
    assert "Comparables Basis" not in h
    # but still renders flags from the valuation's own risk.flags
    assert "Customer concentration" in h


def test_render_unknown_format_errors():
    with pytest.raises(ValueError):
        render(VAL_RESULT, fmt="pdf")


def test_html_escapes_input():
    bad = dict(VAL_RESULT, target_name="<script>alert(1)</script>")
    h = build_html(bad)
    assert "<script>alert(1)</script>" not in h
    assert "&lt;script&gt;" in h


# ---------------------------------------------------------------------------
# Primitive contract
# ---------------------------------------------------------------------------
def test_invoke_ok_html():
    env = invoke({"result": ORCH_RESULT, "format": "html"})
    assert env["ok"] is True
    assert env["result"]["format"] == "html"
    assert env["result"]["length"] > 0
    assert "Acme Co" in env["result"]["content"]


def test_invoke_markdown():
    env = invoke({"result": VAL_RESULT, "format": "md"})
    assert env["ok"] is True
    assert env["result"]["content"].startswith("# Valuation Report")


def test_invoke_missing_result_errors():
    env = invoke({"format": "html"})
    assert env["ok"] is False
    assert env["error"]["type"] == "ValueError"


def test_determinism():
    a = invoke({"result": ORCH_RESULT, "format": "html", "options": {"as_of": "June 2026"}})
    b = invoke({"result": ORCH_RESULT, "format": "html", "options": {"as_of": "June 2026"}})
    assert a == b


# ---------------------------------------------------------------------------
# Optional DOCX
# ---------------------------------------------------------------------------
def test_plain_english_report_html():
    from report import render
    h = render(ORCH_RESULT, "html", {"style": "plain"})
    assert "Plain-English" in h or "plain-english" in h.lower()
    assert "What is" in h and "worth" in h
    assert "no finance background" in h.lower()
    assert "Questions worth asking" in h
    # explains a risk in plain terms, not just the label
    assert "one or a few customers" in h.lower() or "current owner" in h.lower()


def test_plain_english_includes_diligence():
    from report import render
    result = dict(ORCH_RESULT)
    result["diligence"] = dict(ORCH_RESULT["diligence"],
                               completion_pct=0,
                               risk_profile=[{"category": "Customers", "level": "high", "open_items": 3},
                                             {"category": "People", "level": "medium", "open_items": 2}])
    h = render(result, "html", {"style": "plain"})
    assert "How thoroughly it" in h
    assert "preliminary" in h.lower()          # 0% completion messaging
    assert "Customers (high concern)" in h     # per-area concern summary


def test_plain_english_markdown():
    from report import render
    m = render(ORCH_RESULT, "markdown", {"style": "plain"})
    assert m.startswith("# Plain-English Valuation")
    assert "fair-price zone" in m
    assert "A few terms, briefly" in m


def test_plain_style_via_invoke():
    env = invoke({"result": ORCH_RESULT, "format": "html", "options": {"style": "plain"}})
    assert env["ok"] and "worth" in env["result"]["content"].lower()


def test_investor_bank_fragment():
    from report import build_investor_bank
    frag = build_investor_bank({
        "bank_type": "universal_bank", "roe": 0.10,
        "approaches": {"price_to_book": {"low": 120e9, "high": 240e9},
                       "price_to_earnings": {"low": 96e9, "high": 156e9}},
        "recommended_range": {"low": 108e9, "high": 198e9, "mid": 153e9}})
    assert "net worth" in frag.lower() and "return on equity" in frag.lower()
    assert "not financial advice" in frag.lower()


def test_investor_sotp_fragment():
    from report import build_investor_sotp
    frag = build_investor_sotp({
        "conglomerate_discount": 0.10,
        "segments": [{"name": "Cloud", "value_range": {"low": 100, "high": 200}},
                     {"name": "Retail", "value_range": {"low": 50, "high": 90}}],
        "equity_range": {"low": 135, "high": 261, "mid": 198}})
    assert "Cloud" in frag and "Retail" in frag
    assert "separately" in frag.lower()


def test_docx_written_when_available(tmp_path):
    docx = pytest.importorskip("docx")  # noqa: F841
    from report import write_docx
    out = tmp_path / "report.docx"
    write_docx(ORCH_RESULT, str(out))
    assert out.exists() and out.stat().st_size > 0
