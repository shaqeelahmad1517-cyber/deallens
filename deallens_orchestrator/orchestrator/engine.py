"""DealLens orchestrator — chains the three primitives into one evaluation.

    diligence.invoke(checklist) --> red_flags ----\
                                                    >--> valuation.invoke(deal)
    comparables.invoke(query)  --> market band ---/

Resilient by design: if diligence or comparables fails, the orchestrator records
the failure, falls back to safe defaults, and still returns a valuation. Only a
valuation failure (or missing engines) yields an overall error.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import _deps  # noqa: F401  (side effect: put sibling engines on sys.path)

ENGINE_NAME = "deallens.orchestrator"
ENGINE_VERSION = "1.0.0"

_GROWTH_FROM_TREND = {"growing": "growing", "flat": "flat", "declining": "declining"}


def _load_engines():
    """Import the three sibling primitives; raise a clear error if missing."""
    try:
        import valuation_engine
        import diligence_engine
        import comparables
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "Could not import the engine primitives. Keep the deallens_* folders "
            "side by side, or set DEALLENS_HOME to their parent directory. "
            f"Underlying import error: {exc}"
        )
    return valuation_engine, diligence_engine, comparables


def _reported_ebitda_plus_adjustments(financials: Dict[str, Any],
                                      adjustments: List[Dict[str, Any]]) -> float:
    base = (
        float(financials.get("net_income", 0) or 0)
        + float(financials.get("interest", 0) or 0)
        + float(financials.get("taxes", 0) or 0)
        + float(financials.get("depreciation", 0) or 0)
        + float(financials.get("amortization", 0) or 0)
    )
    for a in adjustments or []:
        amt = float(a.get("amount", 0) or 0)
        base += amt if a.get("type", "add_back") == "add_back" else -amt
    return base


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a JSON object (dict)")

    valuation_engine, diligence_engine, comparables = _load_engines()

    target = payload.get("target_name", "")
    financials = payload.get("financials") or {}
    adjustments = payload.get("adjustments") or []

    steps: Dict[str, Any] = {}
    warnings: List[str] = []

    # ---- Step 1: diligence -------------------------------------------------
    red_flags: List[Dict[str, str]] = []
    diligence_result: Optional[Dict[str, Any]] = None
    checklist = payload.get("checklist")
    if checklist:
        cl = dict(checklist)
        cl.setdefault("target_name", target)
        env = diligence_engine.invoke(cl)
        steps["diligence"] = {"ok": env["ok"]}
        if env["ok"]:
            diligence_result = env["result"]
            red_flags = diligence_engine.to_valuation_risk_flags(diligence_result)
        else:
            steps["diligence"]["error"] = env["error"]
            warnings.append(f"diligence failed: {env['error']['message']}; proceeding with no risk flags")
    else:
        steps["diligence"] = {"ok": True, "skipped": True}

    # ---- Step 2: comparables ----------------------------------------------
    market: Optional[Dict[str, Any]] = None
    comparables_result: Optional[Dict[str, Any]] = None
    comp_query = payload.get("comparables")
    if comp_query:
        q = dict(comp_query)
        # Auto-derive size from financials if not supplied.
        if q.get("size_ebitda") is None:
            q["size_ebitda"] = _reported_ebitda_plus_adjustments(financials, adjustments)
        # Auto-derive growth from the diligence revenue_trend signal if not supplied.
        if not q.get("growth") and checklist:
            trend = str((checklist.get("signals") or {}).get("revenue_trend", "")).lower()
            if trend in _GROWTH_FROM_TREND:
                q["growth"] = _GROWTH_FROM_TREND[trend]
        env = comparables.invoke(q)
        steps["comparables"] = {"ok": env["ok"]}
        if env["ok"]:
            comparables_result = env["result"]
            market = comparables.to_valuation_market(comparables_result)
        else:
            steps["comparables"]["error"] = env["error"]
            warnings.append(f"comparables failed: {env['error']['message']}; using provided/default market")
    else:
        steps["comparables"] = {"ok": True, "skipped": True}

    # Market resolution order: comparables -> explicit payload.market -> engine default.
    if market is None and payload.get("market"):
        market = payload["market"]

    # ---- Step 3: valuation -------------------------------------------------
    deal: Dict[str, Any] = {"target_name": target, "financials": financials}
    if adjustments:
        deal["adjustments"] = adjustments
    if market:
        deal["market"] = market
    if red_flags:
        deal["risk_flags"] = red_flags
    for k in ("income", "weights", "enabled_approaches"):
        if payload.get(k) is not None:
            deal[k] = payload[k]

    val_env = valuation_engine.invoke(deal)
    steps["valuation"] = {"ok": val_env["ok"]}
    if not val_env["ok"]:
        steps["valuation"]["error"] = val_env["error"]
        raise RuntimeError(f"valuation failed: {val_env['error']['message']}")
    valuation_result = val_env["result"]

    # ---- Assemble recommendation ------------------------------------------
    rr = valuation_result["recommended_range"]
    key_risks = [f["label"] for f in (red_flags[:3] if red_flags else [])]
    recommendation = {
        "range": rr,
        "headline": (
            f"Indicative value {rr['low']:,.0f}-{rr['high']:,.0f} "
            f"(mid {rr['mid']:,.0f})"
        ),
        "risk_multiple_discount": valuation_result["risk"]["multiple_discount"],
        "key_risks": key_risks,
        "diligence_completion_pct": (diligence_result or {}).get("completion_pct"),
    }

    return {
        "engine": ENGINE_NAME,
        "version": ENGINE_VERSION,
        "target_name": target,
        "steps": steps,
        "warnings": warnings,
        "diligence": diligence_result,
        "comparables": comparables_result,
        "valuation": valuation_result,
        "recommendation": recommendation,
        "disclaimer": (
            "Decision-support only. Aggregates user-supplied data through standard "
            "methodologies; not financial, legal, or valuation advice."
        ),
    }


class Orchestrator:
    name = ENGINE_NAME
    version = ENGINE_VERSION

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return run(payload)
