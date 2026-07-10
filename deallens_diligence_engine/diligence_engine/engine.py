"""DealLens diligence engine — deterministic orchestrator.

Pure function of its input ``Checklist``: instantiates a template, rolls up
completion and risk, and detects red flags (from item ratings + signals).
Crucially, it emits red flags in the shape the valuation engine consumes, so
the two primitives interlock on the spine.
"""
from __future__ import annotations

from typing import Dict, List

from . import rules, templates
from .models import (
    Category, Checklist, ItemState, ItemStatus, RiskRating, RISK_SCORE,
)

ENGINE_NAME = "deallens.diligence"
ENGINE_VERSION = "1.0.0"

_SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}

# Provisional (reduced) valuation impact for UNCONFIRMED AI findings — about half
# the confirmed-flag defaults. Confirming a finding on the checklist applies full
# weight. Kept modest so the AI's first-pass reading nudges, not dominates.
_PROV_MULTIPLE_DISCOUNT = {"low": 0.01, "medium": 0.025, "high": 0.06}
_PROV_RATE_PREMIUM = {"low": 0.0025, "medium": 0.0075, "high": 0.015}
# Map an AI finding onto the diligence/signal category vocabulary by keyword, so a
# finding dedupes against a confirmed signal in the same area AND many findings
# collapse into a few areas (rather than stacking one discount each). The AI's
# category field is inconsistent (e.g. "Customers" vs "customer_concentration"),
# so we match on the category + finding text together.
_CAT_KEYWORDS = [
    ("Customers", ("customer", "client")),
    ("Operations", ("supplier", "supply chain", "vendor", "commodity", "operational",
                    "recall", "product liability", "manufacturing", "inventory", "logistics")),
    ("Legal", ("litigation", "lawsuit", "legal", "regulatory", "regulation", "environmental",
               "compliance", "governance", "related party", "antitrust")),
    ("People", ("owner", "key person", "key-person", "management", "personnel",
                "employee", "founder", "labor", "union")),
    ("Tax", ("tax",)),
    ("Financial", ("debt", "covenant", "leverage", "goodwill", "impairment", "intangible",
                   "material weakness", "internal control", "liquidity", "refinanc",
                   "solvency", "going concern", "margin", "volume", "revenue", "financial")),
]


def _normalize_category(raw: str, text: str = "") -> str:
    s = f"{raw} {text}".lower()
    for cat, kws in _CAT_KEYWORDS:
        if any(k in s for k in kws):
            return cat
    return raw.replace("_", " ").title() if raw else "General"


def _provisional_flags(ai_findings, taken_categories):
    """Convert unconfirmed AI findings into provisional risk flags, one per area,
    skipping any area already covered by a confirmed signal/item flag."""
    seen = set()
    out: List[Dict[str, object]] = []
    for f in sorted(ai_findings or [],
                    key=lambda x: -_SEVERITY_RANK.get(str(x.get("severity", "")).lower(), 0)):
        sev = str(f.get("severity", "medium")).lower()
        if sev not in _PROV_MULTIPLE_DISCOUNT:
            sev = "medium"
        text = str(f.get("finding") or f.get("label") or "").strip()
        cat = _normalize_category(str(f.get("category", "")).strip(), text)
        if cat in taken_categories or cat in seen:
            continue                              # already counted (don't double-dip)
        seen.add(cat)
        out.append({
            "label": "(from report, unconfirmed) " + (text[:160] or cat),
            "severity": sev, "category": cat, "source": "ai_finding",
            "concern": "ai:" + cat, "provisional": True,
            "multiple_discount": _PROV_MULTIPLE_DISCOUNT[sev],
            "discount_rate_premium": _PROV_RATE_PREMIUM[sev],
        })
    return out


def _merge_flags(flags: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Dedupe flags, keeping the highest severity per concern.

    Flags carrying the same ``concern`` key (e.g. an item-level and a
    signal-level flag for customer concentration) collapse to one so the same
    underlying risk isn't double-counted downstream. Flags without a concern
    dedupe on their label.
    """
    best: Dict[str, Dict[str, str]] = {}
    for f in flags:
        key = f.get("concern") or f["label"]
        if key not in best or _SEVERITY_RANK[f["severity"]] > _SEVERITY_RANK[best[key]["severity"]]:
            best[key] = f
    # Sort high -> low severity, then label.
    return sorted(best.values(), key=lambda f: (-_SEVERITY_RANK[f["severity"]], f["label"]))


def run(checklist: Checklist) -> Dict[str, object]:
    template = templates.get_template(checklist.business_type)
    states: Dict[str, ItemState] = {s.id: s for s in checklist.items}

    # --- Build instantiated items + completion/risk roll-up ------------------
    items_out: List[Dict[str, object]] = []
    cat_totals: Dict[str, Dict[str, float]] = {}
    applicable_weight = 0.0
    complete_weight = 0.0
    item_flags: List[Dict[str, str]] = []

    for tmpl in template:
        st = states.get(tmpl.id, ItemState(id=tmpl.id))
        status = st.status
        rating = st.risk_rating
        cat = tmpl.category.value

        is_applicable = status != ItemStatus.NA
        if is_applicable:
            applicable_weight += tmpl.weight
            if status == ItemStatus.COMPLETE:
                complete_weight += tmpl.weight

        cat_totals.setdefault(cat, {"score_sum": 0.0, "rated": 0.0, "open": 0.0, "total": 0.0})
        cat_totals[cat]["total"] += 1
        if rating != RiskRating.NONE:
            cat_totals[cat]["score_sum"] += RISK_SCORE[rating]
            cat_totals[cat]["rated"] += 1
        if status in (ItemStatus.NOT_STARTED, ItemStatus.IN_PROGRESS):
            cat_totals[cat]["open"] += 1

        # Item-level red flags: explicitly flagged, or high-risk, or critical+high.
        if status == ItemStatus.FLAGGED or rating == RiskRating.HIGH:
            sev = "high" if (rating == RiskRating.HIGH or tmpl.critical) else "medium"
            item_flags.append({
                "label": f"{tmpl.prompt}" + (f" — {st.notes}" if st.notes else ""),
                "severity": sev,
                "category": cat,
                "source": "item",
                "concern": tmpl.concern,
            })

        items_out.append({
            "id": tmpl.id,
            "category": cat,
            "prompt": tmpl.prompt,
            "status": status.value,
            "risk_rating": rating.value,
            "critical": tmpl.critical,
            "notes": st.notes,
            "evidence": st.evidence,
        })

    completion_pct = round(100.0 * complete_weight / applicable_weight, 1) if applicable_weight else 0.0

    # --- Category risk profile ----------------------------------------------
    risk_profile = []
    overall_score_sum = 0.0
    overall_rated = 0.0
    for cat, t in sorted(cat_totals.items()):
        avg = (t["score_sum"] / t["rated"]) if t["rated"] else 0.0
        overall_score_sum += t["score_sum"]
        overall_rated += t["rated"]
        level = "high" if avg >= 2.5 else "medium" if avg >= 1.5 else "low" if avg > 0 else "none"
        risk_profile.append({
            "category": cat,
            "avg_risk_score": round(avg, 2),
            "level": level,
            "items": int(t["total"]),
            "open_items": int(t["open"]),
        })

    overall_avg = round(overall_score_sum / overall_rated, 2) if overall_rated else 0.0
    overall_level = "high" if overall_avg >= 2.5 else "medium" if overall_avg >= 1.5 else "low" if overall_avg > 0 else "none"

    # --- Red flags: signals + item-level, merged ----------------------------
    signal_flags = [
        {"label": f.label, "severity": f.severity, "category": f.category,
         "source": f.source, "concern": f.concern}
        for f in rules.detect_from_signals(checklist.signals)
    ]
    red_flags = _merge_flags(signal_flags + item_flags)

    # Unconfirmed AI findings -> provisional flags (skip areas already flagged).
    provisional_flags = _provisional_flags(
        checklist.ai_findings, {f["category"] for f in red_flags})

    return {
        "engine": ENGINE_NAME,
        "version": ENGINE_VERSION,
        "target_name": checklist.target_name,
        "business_type": checklist.business_type,
        "summary": {
            "total_items": len(template),
            "completion_pct": completion_pct,
            "overall_risk_score": overall_avg,
            "overall_risk_level": overall_level,
            "red_flag_count": len(red_flags),
            "provisional_flag_count": len(provisional_flags),
        },
        "completion_pct": completion_pct,
        "risk_profile": risk_profile,
        "red_flags": red_flags,
        "provisional_flags": provisional_flags,
        "items": items_out,
        "disclaimer": (
            "Decision-support only. A structured aid to investigation, not "
            "financial, legal, or accounting advice."
        ),
    }


def to_valuation_risk_flags(result: Dict[str, object]) -> List[Dict[str, str]]:
    """Adapter: diligence result -> valuation-engine `risk_flags` payload.

    This is the interlock. Pass the output straight into the valuation
    engine's input under the ``risk_flags`` key.
    """
    out: List[Dict[str, str]] = []
    for f in list(result.get("red_flags", [])) + list(result.get("provisional_flags", [])):
        flag = {"label": f["label"], "severity": f["severity"], "category": f["category"]}
        # Provisional AI-finding flags carry explicit (reduced) deltas; pass them through.
        if f.get("multiple_discount") is not None:
            flag["multiple_discount"] = f["multiple_discount"]
        if f.get("discount_rate_premium") is not None:
            flag["discount_rate_premium"] = f["discount_rate_premium"]
        out.append(flag)
    return out


class DiligenceEngine:
    name = ENGINE_NAME
    version = ENGINE_VERSION

    def run(self, checklist: Checklist) -> Dict[str, object]:
        return run(checklist)

    def run_dict(self, payload: Dict[str, object]) -> Dict[str, object]:
        return run(Checklist.from_dict(payload))
