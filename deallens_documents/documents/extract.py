"""Core extraction: turn rows/text of a financial statement into a financials block.

Pure (no file or library deps): parses numbers robustly and maps line-item labels
to canonical fields by synonym. Hardened against the silent-error cases that
matter most in real statements: thousands/millions scaling, European number
formats, signed losses, contra-revenue collisions, and stray footnote/year cells.

Philosophy: best-effort + transparent. Returns what it matched, what it couldn't,
and warnings — for a human to confirm. Never silently guesses a value into place.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# Canonical fields, matched in priority order. (field, synonyms, excludes).
# A label matches if it contains a synonym and none of the excludes.
_FIELD_SYNONYMS: List[Tuple[str, List[str], List[str]]] = [
    ("revenue",
     ["total revenue", "total net revenue", "net revenue", "net sales", "total sales",
      "gross sales", "turnover", "gross revenue", "revenue"],
     ["cost", "deferred", "unearned", "per ", "growth", "%", "ratio",
      "returns", "allowance", "other", "discount"]),
    ("net_income",
     ["net income", "net profit", "net earnings", "profit after tax",
      "profit for the year", "profit for the period", "net income (loss)",
      "net loss", "loss for the year", "loss after tax", "loss for the period"],
     ["before", "margin", "%", "operating", "gross"]),
    ("interest", ["interest expense", "interest paid", "interest"],
     ["income", "receivable", "rate"]),
    ("taxes", ["income tax expense", "provision for income tax", "income taxes",
               "income tax", "tax expense", "taxes"],
     ["deferred", "payable", "rate", "before", "after", "paid", "refund", "receivable"]),
    ("depreciation", ["depreciation"], ["accumulated"]),
    ("amortization", ["amortization", "amortisation"], ["accumulated"]),
    ("owner_compensation",
     ["owner compensation", "owner's compensation", "owner salary", "owner's salary",
      "officer compensation", "officer's compensation", "owner draw", "owner's draw",
      "director's remuneration", "owners compensation"], []),
    ("total_assets", ["total assets"], ["current", "non-current", "fixed", "intangible"]),
    ("total_liabilities", ["total liabilities"], ["current", "non-current"]),
]

_ADJUSTMENT_HINTS = [
    "owner", "personal", "one-time", "one time", "one-off", "one off", "non-recurring",
    "nonrecurring", "discretionary", "add-back", "addback", "vehicle", "car", "travel",
    "entertainment", "extraordinary",
]

_NUM_TOKEN = re.compile(r"\(?-?[\$£€¥]?\s?[\d][\d,.’'\s]*(?:\.\d+)?\s?(?:k|m|bn|b)?\)?", re.I)


def parse_number(s: Any) -> Optional[float]:
    """Parse a financial number, locale-aware.

    Handles: $ £ € ¥ symbols, thousands separators (',' '.' space apostrophe),
    decimal points/commas (US and European), () and unicode-minus negatives,
    trailing-minus, and k/m/bn suffixes.
    """
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    t = str(s).strip().replace("−", "-")  # normalize unicode minus
    if not t or t.endswith("%"):
        return None

    neg = False
    if t.startswith("(") and t.endswith(")"):
        neg, t = True, t[1:-1]
    if t.startswith("-"):
        neg, t = True, t[1:]
    if t.endswith("-"):           # trailing-minus (accounting/SAP exports)
        neg, t = True, t[:-1]

    for ch in "$£€¥ ’'":      # currency, spaces, apostrophes (NOT . or , yet)
        t = t.replace(ch, "")
    t = t.strip()

    # Capture a k/m/bn suffix before separator handling.
    suf = ""
    m = re.search(r"(k|m|bn|b)$", t, re.I)
    if m:
        suf = m.group(1).lower()
        t = t[: m.start()]

    has_comma, has_dot = "," in t, "." in t
    if has_comma and has_dot:
        # The rightmost separator is the decimal point.
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif has_comma:
        parts = t.split(",")
        # "12,50" -> decimal; "4,200" / "1,234,567" -> thousands.
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            t = t.replace(",", ".")
        else:
            t = t.replace(",", "")
    elif has_dot:
        parts = t.split(".")
        if len(parts) > 2:                       # 1.234.567 -> European thousands
            t = t.replace(".", "")
        # else single dot: keep as US decimal (ambiguous 1.234 stays 1.234)

    if not re.fullmatch(r"\d*\.?\d+", t):
        return None
    val = float(t) * {"k": 1e3, "m": 1e6, "b": 1e9, "bn": 1e9}.get(suf, 1.0)
    return -val if neg else val


def _match_field(label: str, already: set) -> Optional[str]:
    low = label.lower().strip()
    for field, syns, excludes in _FIELD_SYNONYMS:
        if field in already:
            continue
        if any(x in low for x in excludes):
            continue
        if any(syn in low for syn in syns):
            return field
    return None


def _select_number(cells: List[str]) -> Tuple[Optional[float], bool]:
    """Pick the value cell, ignoring year/footnote noise. Returns (value, ambiguous)."""
    nums = [n for n in (parse_number(c) for c in cells) if n is not None]
    if not nums:
        return None, False
    big = max(abs(x) for x in nums)

    def is_noise(x: float) -> bool:
        if abs(x) == big:
            return False
        if float(x).is_integer():
            ax = abs(x)
            if 1900 <= ax <= 2099:   # year column
                return True
            if ax < 100:             # footnote / note reference
                return True
        return False

    filtered = [x for x in nums if not is_noise(x)] or nums
    chosen = max(filtered, key=abs)
    ambiguous = sum(1 for x in filtered if abs(x) >= 0.1 * abs(chosen)) > 1
    return chosen, ambiguous


def _detect_scale(labels: List[str]) -> Tuple[float, Optional[str]]:
    blob = " ".join(l.lower() for l in labels)
    for kw, mult, name in [
        ("in billion", 1e9, "billions"), ("$bn", 1e9, "billions"),
        ("in million", 1e6, "millions"), ("$m", 1e6, "millions"), ("in mn", 1e6, "millions"),
        ("in thousand", 1e3, "thousands"), ("$'000", 1e3, "thousands"),
        ("'000", 1e3, "thousands"), ("$000", 1e3, "thousands"), ("(000", 1e3, "thousands"),
    ]:
        if kw in blob:
            return mult, name
    return 1.0, None


def _make_pairs_from_rows(rows: List[List[Any]]) -> Tuple[List[Tuple[str, Optional[float]]], bool]:
    pairs: List[Tuple[str, Optional[float]]] = []
    multi_col = False
    for row in rows:
        cells = [str(c).strip() for c in row if str(c).strip() != ""]
        if not cells:
            continue
        label = cells[0]
        value, amb = _select_number(cells[1:])
        multi_col = multi_col or amb
        if value is None and len(cells) == 1:
            nums = _NUM_TOKEN.findall(label)
            if nums:
                value = parse_number(nums[-1])
                label = label[: label.rfind(nums[-1])].strip(" .:-\t")
        pairs.append((label, value))
    return pairs, multi_col


def _make_pairs_from_text(text: str) -> List[Tuple[str, Optional[float]]]:
    pairs: List[Tuple[str, Optional[float]]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        nums = _NUM_TOKEN.findall(line)
        if nums:
            # choose the largest-magnitude token (avoids years/footnotes)
            best = max(nums, key=lambda x: abs(parse_number(x) or 0))
            label = line[: line.rfind(best)].strip(" .:-\t|")
            pairs.append((label or line, parse_number(best)))
        else:
            pairs.append((line, None))
    return pairs


def extract_from_pairs(pairs: List[Tuple[str, Optional[float]]]) -> Dict[str, Any]:
    labels = [p[0] for p in pairs]
    scale, scale_name = _detect_scale(labels)

    financials: Dict[str, float] = {}
    line_items: List[Dict[str, Any]] = []
    adjustment_candidates: List[Dict[str, Any]] = []
    unmatched: List[str] = []
    found_fields: set = set()

    for label, raw_value in pairs:
        value = parse_number(raw_value)
        field = _match_field(label, found_fields) if label else None
        if field and value is not None:
            # A "loss" line shown as a positive number is economically negative.
            if field == "net_income" and "loss" in label.lower() and value > 0:
                value = -value
            value *= scale
            financials[field] = value
            found_fields.add(field)
            line_items.append({"field": field, "label": label, "value": value})
            continue
        low = (label or "").lower()
        if value is not None and any(h in low for h in _ADJUSTMENT_HINTS):
            adjustment_candidates.append({"label": label, "amount": abs(value) * scale, "type": "add_back"})
        elif label:
            unmatched.append(label)

    # --- Reliability guard -------------------------------------------------
    # This extractor matches line-item LABELS in a *clean statement*. Fed a full
    # annual report (dozens of prose pages), it grabs footnote numbers, mis-reads
    # the scale from stray words like "billion", and collides fields — producing
    # nonsense (the "$32 quadrillion" bug). Detect those conditions and refuse,
    # rather than return a plausible-looking but wrong number.
    _ABSURD = 2e12  # no single line item (revenue/NI/assets) realistically exceeds ~$2T
    absurd = [k for k, v in financials.items() if abs(v) > _ABSURD]
    assets_eq_liab = (
        financials.get("total_assets") is not None
        and financials.get("total_assets") == financials.get("total_liabilities")
    )
    looks_like_report = len(pairs) > 200  # a clean statement is short; a report is thousands of lines
    if absurd or assets_eq_liab or looks_like_report:
        return {
            "financials": {},
            "line_items": [],
            "adjustment_candidates": [],
            "unmatched": [],
            "fields_found": 0,
            "scale": scale,
            "reliable": False,
            "warnings": [
                "This looks like a full report or narrative document, not a single "
                "financial statement. Automatic label-reading is unreliable here, so no "
                "figures were extracted. For a full annual report use “Read full "
                "report (AI)”; otherwise paste just the income statement / balance "
                "sheet, or upload a clean CSV/Excel statement."
            ],
        }

    warnings: List[str] = []
    if scale_name:
        warnings.append(f"Figures appear to be stated in {scale_name} — scaled by {int(scale):,}. Verify.")
    for required in ("revenue", "net_income"):
        if required not in financials:
            warnings.append(f"{required} not found — please enter it manually")

    return {
        "financials": financials,
        "line_items": line_items,
        "adjustment_candidates": adjustment_candidates,
        "unmatched": unmatched,
        "fields_found": len(financials),
        "scale": scale,
        "reliable": True,
        "warnings": warnings,
    }


def extract_from_rows(rows: List[List[Any]]) -> Dict[str, Any]:
    pairs, multi_col = _make_pairs_from_rows(rows)
    result = extract_from_pairs(pairs)
    if multi_col:
        result["warnings"].append(
            "Multiple value columns detected (e.g. multi-year) — verify the intended period was used."
        )
    return result


def extract_from_text(text: str) -> Dict[str, Any]:
    return extract_from_pairs(_make_pairs_from_text(text))
