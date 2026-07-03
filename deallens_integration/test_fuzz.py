"""End-to-end fuzz / property tests across the whole DealLens pipeline.

Throws hundreds of randomized, deliberately-nasty deals (loss-making, insolvent,
empty, huge, missing fields, bad sectors) through the assembled system and
asserts invariants that must ALWAYS hold. Randomness is seeded so any failure is
reproducible from the reported case index.
"""
import random
import string

import pytest

import comparables  # noqa: E402
import documents  # noqa: E402
import orchestrator  # noqa: E402
import quickscreen  # noqa: E402
import report  # noqa: E402
import valuation_engine  # noqa: E402

SECTORS = comparables.available_sectors() + ["atlantis", "", "TRUCKING"]
METRICS = ["sde", "ebitda", "revenue", "bogus"]
BUSINESS_TYPES = ["general", "smb", "saas", "retail", "spaceship"]
TRENDS = ["growing", "flat", "declining", ""]
N_CASES = 300


def _rand_financials(rng):
    if rng.random() < 0.1:
        return {}
    sign = rng.choice([1, 1, 1, -1])          # sometimes loss-making
    ni = sign * rng.randint(0, 900_000)
    f = {
        "revenue": rng.randint(0, 8_000_000),
        "net_income": ni,
        "interest": rng.randint(0, 80_000),
        "taxes": rng.randint(0, 200_000),
        "depreciation": rng.randint(0, 150_000),
        "amortization": rng.randint(0, 50_000),
        "owner_compensation": rng.randint(0, 300_000),
        "total_assets": rng.randint(0, 3_000_000),
        "total_liabilities": rng.randint(0, 3_000_000),  # may exceed assets
    }
    # Randomly drop some fields.
    for k in list(f):
        if rng.random() < 0.15:
            del f[k]
    return f


def _rand_payload(rng):
    payload = {"target_name": "Fuzz " + "".join(rng.choice(string.ascii_uppercase) for _ in range(4)),
               "financials": _rand_financials(rng)}
    if rng.random() < 0.8:
        payload["comparables"] = {"sector": rng.choice(SECTORS), "metric": rng.choice(METRICS)}
    if rng.random() < 0.7:
        payload["checklist"] = {
            "business_type": rng.choice(BUSINESS_TYPES),
            "items": [],
            "signals": {
                "top_customer_pct": rng.choice([None, rng.randint(0, 100)]),
                "owner_dependent": rng.choice([True, False, None]),
                "revenue_trend": rng.choice(TRENDS),
            },
        }
    if rng.random() < 0.3:
        payload["enabled_approaches"] = rng.sample(["income", "market", "asset"],
                                                   rng.randint(1, 3))
    return payload


def _check_range(rr, ctx):
    if rr is None:
        return
    assert rr["low"] <= rr["high"], f"inverted range: {rr} [{ctx}]"
    assert rr["low"] >= 0, f"negative range low: {rr} [{ctx}]"
    assert rr["mid"] >= 0, f"negative mid: {rr} [{ctx}]"


def test_orchestrator_fuzz_invariants():
    for i in range(N_CASES):
        rng = random.Random(1000 + i)
        payload = _rand_payload(rng)
        env = orchestrator.invoke(payload)          # must never raise
        assert isinstance(env, dict) and "ok" in env, f"[case {i}] malformed envelope"
        if not env["ok"]:
            assert env["error"]["message"], f"[case {i}] empty error"
            continue
        r = env["result"]
        _check_range(r["recommendation"]["range"], f"case {i} seed {1000+i}")
        # warnings must be a list; loss-making cases should carry warnings
        assert isinstance(r["valuation"].get("warnings", []), list)


def test_report_renders_for_any_valid_result():
    for i in range(120):
        rng = random.Random(5000 + i)
        env = orchestrator.invoke(_rand_payload(rng))
        if not env["ok"]:
            continue
        renv = report.invoke({"result": env["result"], "format": "html"})
        assert "ok" in renv, f"[case {i}] report malformed"
        if renv["ok"]:
            assert renv["result"]["length"] > 0
        else:
            # only acceptable failure is a genuinely value-less result
            assert env["result"]["recommendation"]["range"] is None


def test_quickscreen_fuzz():
    for i in range(200):
        rng = random.Random(9000 + i)
        payload = {"earnings": rng.choice([-1, 1]) * rng.randint(0, 3_000_000),
                   "sector": rng.choice(SECTORS), "metric": rng.choice(METRICS),
                   "growth": rng.choice(TRENDS)}
        env = quickscreen.invoke(payload)
        assert "ok" in env
        if env["ok"]:
            _check_range(env["result"]["range"], f"qs case {i}")


def test_valuation_direct_fuzz():
    for i in range(200):
        rng = random.Random(7000 + i)
        env = valuation_engine.invoke({"financials": _rand_financials(rng),
                                       "market": {"metric": rng.choice(METRICS)}})
        assert "ok" in env
        if env["ok"]:
            _check_range(env["result"]["recommended_range"], f"val case {i}")


def test_documents_number_parser_never_crashes():
    charset = "0123456789.,()-$€£ '−kmbn%KMxy/"
    for i in range(500):
        rng = random.Random(3000 + i)
        s = "".join(rng.choice(charset) for _ in range(rng.randint(0, 14)))
        out = documents.parse_number(s)              # must never raise
        assert out is None or isinstance(out, float)


def test_documents_ingest_random_text_never_crashes():
    words = ["Revenue", "Net income", "Net loss", "Total assets", "Owner salary",
             "Cost of sales", "Depreciation", "in thousands", "(in millions)"]
    for i in range(150):
        rng = random.Random(4000 + i)
        lines = []
        for _ in range(rng.randint(0, 8)):
            lbl = rng.choice(words)
            val = rng.choice(["", f"{rng.randint(0,9_000_000):,}", f"({rng.randint(0,900):,})",
                              "1.234,56", "n/a", f"{rng.randint(0,100)}%"])
            lines.append(f"{lbl} {val}")
        env = documents.invoke({"text": "\n".join(lines)})
        assert env["ok"] is True
        assert isinstance(env["result"]["financials"], dict)
