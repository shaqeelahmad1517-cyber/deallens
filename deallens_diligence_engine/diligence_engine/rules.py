"""Signal-based red-flag detection.

Each rule inspects the structured ``signals`` dict on a checklist and, if its
condition holds, emits a red flag. Rules are data-driven and pure. Severities
(low/medium/high) match the valuation engine's RiskFlag severities so output
flags can be consumed directly downstream.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, NamedTuple


class Flag(NamedTuple):
    label: str
    severity: str
    category: str
    source: str = "signal"
    concern: str = ""    # shared key to dedupe against item-level flags


def _num(signals: Dict[str, Any], key: str):
    v = signals.get(key)
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _rule_customer_concentration(s: Dict[str, Any]) -> List[Flag]:
    pct = _num(s, "top_customer_pct")
    if pct is None:
        return []
    if pct >= 35:
        return [Flag(f"Customer concentration: top customer = {pct:.0f}% of revenue", "high", "Customers", concern="customer_concentration")]
    if pct >= 20:
        return [Flag(f"Customer concentration: top customer = {pct:.0f}% of revenue", "medium", "Customers", concern="customer_concentration")]
    return []


def _rule_supplier_concentration(s: Dict[str, Any]) -> List[Flag]:
    pct = _num(s, "top_supplier_pct")
    if pct is None:
        return []
    if pct >= 40:
        return [Flag(f"Supplier concentration: top supplier = {pct:.0f}% of COGS", "high", "Operations", concern="supplier_concentration")]
    if pct >= 25:
        return [Flag(f"Supplier concentration: top supplier = {pct:.0f}% of COGS", "medium", "Operations", concern="supplier_concentration")]
    return []


def _rule_owner_dependence(s: Dict[str, Any]) -> List[Flag]:
    if s.get("owner_dependent") is True:
        has_team = s.get("management_team_in_place") is True
        sev = "medium" if has_team else "high"
        return [Flag("Owner dependence: business relies on the current owner", sev, "People", concern="owner_dependence")]
    return []


def _rule_revenue_trend(s: Dict[str, Any]) -> List[Flag]:
    trend = str(s.get("revenue_trend", "")).lower()
    if trend == "declining":
        return [Flag("Declining revenue trend", "high", "Financial")]
    if trend == "flat":
        return [Flag("Flat revenue (no growth)", "low", "Financial")]
    return []


def _rule_margin_trend(s: Dict[str, Any]) -> List[Flag]:
    if str(s.get("margin_trend", "")).lower() == "declining":
        return [Flag("Declining profit margins", "medium", "Financial")]
    return []


def _rule_books_quality(s: Dict[str, Any]) -> List[Flag]:
    if s.get("clean_books") is False:
        return [Flag("Messy or unavailable financial records", "high", "Financial")]
    return []


def _rule_retention(s: Dict[str, Any]) -> List[Flag]:
    r = _num(s, "customer_retention_pct")
    if r is None:
        return []
    if r < 60:
        return [Flag(f"Weak customer retention ({r:.0f}%)", "high", "Customers", concern="customer_retention")]
    if r < 75:
        return [Flag(f"Below-par customer retention ({r:.0f}%)", "medium", "Customers", concern="customer_retention")]
    return []


def _rule_litigation(s: Dict[str, Any]) -> List[Flag]:
    if s.get("litigation_pending") is True:
        return [Flag("Pending or threatened litigation", "medium", "Legal", concern="litigation")]
    return []


def _rule_contracts_assignable(s: Dict[str, Any]) -> List[Flag]:
    if s.get("contracts_assignable") is False:
        return [Flag("Key contracts not assignable / change-of-control risk", "medium", "Legal")]
    return []


def _rule_lease(s: Dict[str, Any]) -> List[Flag]:
    if s.get("lease_assignable") is False:
        return [Flag("Premises lease not assignable to a new owner", "high", "Operations", concern="lease")]
    return []


def _rule_tax(s: Dict[str, Any]) -> List[Flag]:
    if s.get("taxes_current") is False:
        return [Flag("Outstanding or unfiled taxes", "high", "Tax", concern="taxes")]
    return []


# Registry of all signal rules.
SIGNAL_RULES: List[Callable[[Dict[str, Any]], List[Flag]]] = [
    _rule_customer_concentration,
    _rule_supplier_concentration,
    _rule_owner_dependence,
    _rule_revenue_trend,
    _rule_margin_trend,
    _rule_books_quality,
    _rule_retention,
    _rule_litigation,
    _rule_contracts_assignable,
    _rule_lease,
    _rule_tax,
]


def detect_from_signals(signals: Dict[str, Any]) -> List[Flag]:
    flags: List[Flag] = []
    for rule in SIGNAL_RULES:
        flags.extend(rule(signals or {}))
    return flags
