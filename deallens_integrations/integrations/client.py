"""Fetch financial reports from a provider and map them to a financials block.

The ``transport`` is injectable (same signature as oauth). Mappers turn each
provider's Profit & Loss / Balance Sheet JSON into DealLens's financials shape.

The QuickBooks/Xero mappers follow the providers' documented report structures;
verify against your sandbox data and adjust label matching if needed (their
report layouts are configurable per account).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import providers
from .oauth import Transport, urllib_transport

# Reuse the hardened label matcher from the documents primitive when available;
# fall back to a tiny local matcher so this package works standalone.
try:  # pragma: no cover - path dependent
    import documents
    _match = None  # we use documents.extract_from_rows below
except Exception:  # pragma: no cover
    documents = None


_LABELS = {
    "revenue": ["total income", "total revenue", "income", "revenue", "total operating revenue"],
    "net_income": ["net income", "net profit", "profit for the period", "net earnings", "net income (loss)"],
    "interest": ["interest expense", "interest"],
    "taxes": ["income tax", "tax expense", "taxes"],
    "depreciation": ["depreciation"],
    "amortization": ["amortization", "amortisation"],
    "total_assets": ["total assets"],
    "total_liabilities": ["total liabilities"],
}


def _local_match(rows: List[List[str]]) -> Dict[str, float]:
    """Match using provider-specific labels (e.g. QuickBooks/Xero 'Total Income')."""
    out: Dict[str, float] = {}
    for label, value in rows:
        low = str(label).lower()
        try:
            v = float(str(value).replace(",", "").replace("$", ""))
        except (TypeError, ValueError):
            continue
        for field, syns in _LABELS.items():
            if field not in out and any(s in low for s in syns):
                out[field] = v
                break
    return out


def _match_rows(rows: List[List[str]]) -> Dict[str, float]:
    """Map [label, value] rows -> financials.

    Provider-specific labels (Total Income, Net Profit, ...) are matched first,
    then the hardened documents extractor fills any remaining gaps.
    """
    result = _local_match(rows)
    if documents is not None:
        for k, v in documents.extract_from_rows(rows)["financials"].items():
            result.setdefault(k, v)
    return result


# --- QuickBooks -------------------------------------------------------------
def _qb_rows(report: Dict[str, Any]) -> List[List[str]]:
    """Flatten a QuickBooks report (nested Rows/ColData) into [label, value]."""
    rows: List[List[str]] = []

    def walk(node):
        if isinstance(node, dict):
            if "ColData" in node:
                cols = node["ColData"]
                if cols:
                    label = cols[0].get("value", "")
                    value = cols[-1].get("value", "") if len(cols) > 1 else ""
                    if label:
                        rows.append([label, value])
            for key in ("Rows", "Row", "Summary"):
                if key in node:
                    walk(node[key])
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(report.get("Rows", report))
    # Summary rows (e.g. "Total Income") often live under 'Summary'
    return rows


def _num(v):
    if documents is not None:
        return documents.parse_number(v)
    try:
        return float(str(v).replace(",", "").replace("$", ""))
    except (TypeError, ValueError):
        return None


def _qb_groups(report: Dict[str, Any]) -> Dict[str, str]:
    """Collect QuickBooks summary rows keyed by their authoritative ``group``
    attribute (Income, NetIncome, TotalAssets, ...) — reliable, unlike labels."""
    out: Dict[str, str] = {}

    def walk(node):
        if isinstance(node, dict):
            grp = node.get("group")
            summ = node.get("Summary")
            if grp and isinstance(summ, dict) and "ColData" in summ:
                cols = summ["ColData"]
                if len(cols) > 1:
                    out[grp] = cols[-1].get("value", "")
            for key in ("Rows", "Row"):
                if key in node:
                    walk(node[key])
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(report.get("Rows", report))
    return out


# QuickBooks report 'group' attributes -> our fields (authoritative section totals).
_QB_GROUPS = {
    "Income": "revenue", "TotalIncome": "revenue",
    "NetIncome": "net_income",
    "TotalAssets": "total_assets",
    "TotalLiabilities": "total_liabilities",
}


def fetch_quickbooks(conn: Dict[str, Any], transport: Transport = urllib_transport) -> Dict[str, Any]:
    base = providers.api_base("quickbooks")
    realm = conn.get("realm_id", "")
    headers = {"Authorization": f"Bearer {conn.get('access_token','')}", "Accept": "application/json"}
    pl = transport("GET", f"{base}/v3/company/{realm}/reports/ProfitAndLoss", headers, None)
    bs = transport("GET", f"{base}/v3/company/{realm}/reports/BalanceSheet", headers, None)

    fin: Dict[str, Any] = {}
    all_pairs = []
    for report in (pl, bs):
        groups = _qb_groups(report)
        for grp, field in _QB_GROUPS.items():
            if field not in fin and grp in groups:
                v = _num(groups[grp])
                if v is not None:
                    fin[field] = v
        all_pairs += _qb_rows(report)
    # Fill remaining fields (interest, taxes, depreciation) via label matching.
    for field, val in _match_rows(all_pairs).items():
        fin.setdefault(field, val)
    return fin


# --- Xero -------------------------------------------------------------------
def _xero_rows(report: Dict[str, Any]) -> List[List[str]]:
    rows: List[List[str]] = []
    reports = report.get("Reports") or [report]
    for rep in reports:
        for section in rep.get("Rows", []):
            for r in section.get("Rows", [section]):
                cells = r.get("Cells", [])
                if len(cells) >= 2:
                    label = cells[0].get("Value", "")
                    value = cells[-1].get("Value", "")
                    if label:
                        rows.append([label, value])
    return rows


def fetch_xero(conn: Dict[str, Any], transport: Transport = urllib_transport) -> Dict[str, Any]:
    base = providers.api_base("xero")
    headers = {
        "Authorization": f"Bearer {conn.get('access_token','')}",
        "Accept": "application/json",
        "Xero-tenant-id": conn.get("realm_id", ""),
    }
    pl = transport("GET", f"{base}/api.xro/2.0/Reports/ProfitAndLoss", headers, None)
    bs = transport("GET", f"{base}/api.xro/2.0/Reports/BalanceSheet", headers, None)
    return _match_rows(_xero_rows(pl) + _xero_rows(bs))


# --- Mock -------------------------------------------------------------------
def fetch_mock(conn: Dict[str, Any], transport: Transport = urllib_transport) -> Dict[str, Any]:
    """A representative pull so the flow is demoable without real accounts."""
    return {
        "revenue": 4_200_000.0, "net_income": 520_000.0, "interest": 40_000.0,
        "taxes": 110_000.0, "depreciation": 90_000.0, "amortization": 20_000.0,
        "total_assets": 1_900_000.0, "total_liabilities": 700_000.0,
    }


_FETCHERS = {"quickbooks": fetch_quickbooks, "xero": fetch_xero, "mock": fetch_mock}


def fetch_financials(provider_key: str, conn: Dict[str, Any],
                     transport: Transport = urllib_transport) -> Dict[str, Any]:
    fetch = _FETCHERS.get(provider_key)
    if not fetch:
        raise ValueError(f"no fetcher for provider {provider_key!r}")
    return fetch(conn, transport)
