"""Pure, deterministic report renderers (HTML and Markdown).

These take a result (orchestrator or valuation) plus optional presentation
options and return a document as a string. No file I/O, no clock — so the
output is reproducible and the primitive stays embeddable.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from .normalize import extract

ACCENT = "#1F4E79"
ACCENT2 = "#2E75B6"
LIGHT = "#D6E4F0"
GREY = "#F2F2F2"

_SEV_COLOR = {"high": "#C0392B", "medium": "#E67E22", "low": "#7F8C8D"}


def _money(n: Optional[float]) -> str:
    if n is None:
        return "—"
    try:
        return f"${float(n):,.0f}"
    except (TypeError, ValueError):
        return str(n)


def _pct(n: Optional[float], scale: float = 1.0) -> str:
    if n is None:
        return "—"
    try:
        return f"{float(n) * scale:.1f}%"
    except (TypeError, ValueError):
        return str(n)


def _x(n: Optional[float]) -> str:
    if n is None:
        return "—"
    try:
        return f"{float(n):.2f}×"
    except (TypeError, ValueError):
        return str(n)


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------
def build_markdown(result: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> str:
    o = options or {}
    d = extract(result)
    rr = d["recommended_range"]
    lines: List[str] = []

    lines.append(f"# Valuation Report — {d['target_name']}")
    meta = []
    if o.get("as_of"):
        meta.append(f"As of {o['as_of']}")
    if o.get("prepared_by"):
        meta.append(f"Prepared by {o['prepared_by']}")
    if meta:
        lines.append("_" + "  ·  ".join(meta) + "_")
    lines.append("")

    lines.append("## Recommended Value Range")
    lines.append("")
    lines.append(f"**{_money(rr.get('low'))} – {_money(rr.get('high'))}**  (midpoint {_money(rr.get('mid'))})")
    lines.append("")

    norm = d["normalization"]
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Normalized EBITDA | {_money(norm.get('normalized_ebitda'))} |")
    lines.append(f"| Seller's Discretionary Earnings (SDE) | {_money(norm.get('sde'))} |")
    lines.append(f"| Risk multiple discount | {_pct(d['risk'].get('multiple_discount'), 100)} |")
    if d["diligence"].get("completion_pct") is not None:
        lines.append(f"| Diligence completion | {d['diligence']['completion_pct']}% |")
    lines.append("")

    lines.append("## Valuation Approaches")
    lines.append("")
    lines.append("| Approach | Result |")
    lines.append("|---|---|")
    ap = d["approaches"]
    if "income" in ap:
        inc = ap["income"]
        dcf = inc.get("dcf", {}).get("value")
        cap = inc.get("capitalization", {}).get("value")
        lines.append(f"| Income — DCF | {_money(dcf)} |")
        lines.append(f"| Income — Capitalization | {_money(cap)} |")
    if "market" in ap:
        mk = ap["market"]
        lines.append(f"| Market — {mk.get('metric','').upper()} {_x(mk.get('low_multiple'))}–{_x(mk.get('high_multiple'))} | "
                     f"{_money(mk.get('low'))} – {_money(mk.get('high'))} |")
    if "asset" in ap:
        lines.append(f"| Asset — Net Asset Value | {_money(ap['asset'].get('value'))} |")
    lines.append("")

    if d["comparables"]:
        c = d["comparables"]
        m = c.get("modifiers", {})
        lines.append("## Comparables Basis")
        lines.append("")
        lines.append(f"Sector **{c.get('sector_matched')}**, {c.get('metric','').upper()} base "
                     f"{c.get('base_band')} → applied **{_x(c.get('low_multiple'))}–{_x(c.get('high_multiple'))}** "
                     f"(size ×{m.get('size_factor')}, growth ×{m.get('growth_factor')}).")
        lines.append("")

    dl = d["diligence"]
    ai_findings = dl.get("ai_findings") or []
    risk_profile = [p for p in (dl.get("risk_profile") or []) if p.get("level") not in (None, "none")]
    if d["red_flags"] or ai_findings or risk_profile:
        lines.append("## Due Diligence")
        lines.append("")
        if dl.get("completion_pct") is not None and dl["completion_pct"] <= 0:
            lines.append("_Checklist not yet worked through — items below are auto-detected from the "
                         "financials and the uploaded document; verify before relying on the valuation._")
            lines.append("")
        if ai_findings:
            lines.append("**Findings from the document** (auto-read — these provisionally reduce the value; confirm each on the checklist for full weight):")
            lines.append("")
            for f in ai_findings:
                lines.append(f"- **[{str(f.get('severity','')).upper()}]** {f.get('category','')}: {f.get('finding','')}")
            lines.append("")
        if d["red_flags"]:
            lines.append("**Red flags** (triggered by the deal's key facts):")
            lines.append("")
            for f in d["red_flags"]:
                lines.append(f"- **[{str(f.get('severity','')).upper()}]** {f.get('category','')}: {f.get('label','')}")
            lines.append("")
        if risk_profile:
            order = {"high": 3, "medium": 2, "low": 1}
            lines.append("**Risk by area:** " + "; ".join(
                f"{p['category']} ({p['level']}, {p.get('open_items', p.get('items',''))} open)"
                for p in sorted(risk_profile, key=lambda p: -order.get(p.get('level'), 0))))
            lines.append("")

    sens = d["sensitivity"].get("discount_rate") if d["sensitivity"] else None
    if sens:
        lines.append("## Sensitivity — DCF vs. Discount Rate")
        lines.append("")
        lines.append("| Discount rate | DCF value |")
        lines.append("|---|---|")
        for row in sens:
            lines.append(f"| {_pct(row.get('discount_rate'), 100)} | {_money(row.get('dcf_value'))} |")
        lines.append("")

    if d["disclaimer"]:
        lines.append("---")
        lines.append(f"_{d['disclaimer']}_")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML (standalone, print-ready)
# ---------------------------------------------------------------------------
def _esc(s: Any) -> str:
    return html.escape(str(s if s is not None else ""))


def _diligence_section_html(d: Dict[str, Any]) -> str:
    """A full due-diligence section: status, findings from the report, auto red
    flags, and the area-by-area risk profile. Renders only the parts present."""
    dl = d.get("diligence", {}) or {}
    red_flags = d.get("red_flags", []) or []
    ai_findings = dl.get("ai_findings", []) or []
    risk_profile = [p for p in (dl.get("risk_profile") or []) if p.get("level") not in (None, "none")]
    completion = dl.get("completion_pct")
    overall = dl.get("overall_risk_level")

    if not (red_flags or ai_findings or risk_profile or completion is not None):
        return ""

    parts = ["<h2>Due Diligence</h2>"]

    status_bits = []
    if completion is not None:
        status_bits.append(f"Checklist completion: <strong>{_esc(completion)}%</strong>")
    if overall:
        status_bits.append(f"Overall risk: <strong>{_esc(str(overall).title())}</strong>")
    if status_bits:
        parts.append(f"<p class='note'>{' · '.join(status_bits)}</p>")
    if completion is not None and completion <= 0:
        parts.append("<p class='note'>The checklist has not been worked through yet — the items "
                     "below are auto-detected from the financials and the uploaded document, and "
                     "should be verified before relying on this valuation.</p>")

    def _finding_list(title, sub, entries, label_key):
        lis = []
        for f in entries:
            sev = str(f.get("severity", "")).lower()
            color = _SEV_COLOR.get(sev, "#7F8C8D")
            text = f.get(label_key) or f.get("finding") or f.get("label") or ""
            lis.append(
                f"<li><span class='badge' style='background:{color}'>{_esc(sev.upper() or '—')}</span>"
                f"<span class='cat'>{_esc(f.get('category',''))}</span>{_esc(text)}</li>")
        return (f"<h3>{title} <span class='sub'>{sub}</span></h3>"
                f"<ul class='flags'>{''.join(lis)}</ul>") if lis else ""

    parts.append(_finding_list("Findings from the document",
                               "(auto-read — these provisionally reduce the value; confirm each on the checklist for full weight)",
                               ai_findings, "finding"))
    parts.append(_finding_list("Red flags", "(triggered by the deal's key facts)", red_flags, "label"))

    if risk_profile:
        order = {"high": 3, "medium": 2, "low": 1}
        rows = "".join(
            f"<tr><td>{_esc(p.get('category',''))}</td>"
            f"<td>{_esc(str(p.get('level','')).title())}</td>"
            f"<td class='num'>{_esc(p.get('open_items', p.get('items','')))}</td></tr>"
            for p in sorted(risk_profile, key=lambda p: -order.get(p.get('level'), 0)))
        parts.append("<h3>Risk by area</h3>"
                     "<table class='grid'><thead><tr><th>Area</th><th>Concern</th>"
                     "<th style='text-align:right'>Open items</th></tr></thead>"
                     f"<tbody>{rows}</tbody></table>")

    return "\n".join(p for p in parts if p)


def build_html(result: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> str:
    o = options or {}
    d = extract(result)
    rr = d["recommended_range"]
    norm = d["normalization"]
    ap = d["approaches"]

    meta_bits = []
    if o.get("as_of"):
        meta_bits.append(f"As of {_esc(o['as_of'])}")
    if o.get("prepared_by"):
        meta_bits.append(f"Prepared by {_esc(o['prepared_by'])}")
    meta = "  ·  ".join(meta_bits)

    # Approaches rows
    rows = []
    if "income" in ap:
        inc = ap["income"]
        rows.append(("Income — Discounted Cash Flow", _money(inc.get("dcf", {}).get("value"))))
        rows.append(("Income — Capitalization of Earnings", _money(inc.get("capitalization", {}).get("value"))))
    if "market" in ap:
        mk = ap["market"]
        label = f"Market — {(_esc(mk.get('metric','')) or '').upper()} {_x(mk.get('low_multiple'))}–{_x(mk.get('high_multiple'))}"
        rows.append((label, f"{_money(mk.get('low'))} – {_money(mk.get('high'))}"))
    if "asset" in ap:
        rows.append(("Asset — Net Asset Value", _money(ap["asset"].get("value"))))
    approach_rows = "\n".join(
        f"<tr><td>{_esc(name)}</td><td class='num'>{_esc(val)}</td></tr>" for name, val in rows
    )

    # --- Comprehensive Due Diligence section -------------------------------
    flags_html = _diligence_section_html(d)

    # Comparables
    comps_html = ""
    if d["comparables"]:
        c = d["comparables"]
        m = c.get("modifiers", {})
        comps_html = (
            "<h2>Comparables Basis</h2>"
            f"<p>Sector <strong>{_esc(c.get('sector_matched'))}</strong>, "
            f"{_esc(str(c.get('metric','')).upper())} base {_esc(c.get('base_band'))} → applied "
            f"<strong>{_x(c.get('low_multiple'))}–{_x(c.get('high_multiple'))}</strong> "
            f"(size ×{_esc(m.get('size_factor'))}, growth ×{_esc(m.get('growth_factor'))}). "
            f"<span class='note'>{_esc(c.get('source',''))}</span></p>"
        )

    # Sensitivity
    sens_html = ""
    sens = d["sensitivity"].get("discount_rate") if d["sensitivity"] else None
    if sens:
        srows = "\n".join(
            f"<tr><td>{_pct(r.get('discount_rate'),100)}</td><td class='num'>{_money(r.get('dcf_value'))}</td></tr>"
            for r in sens
        )
        sens_html = (
            "<h2>Sensitivity — DCF vs. Discount Rate</h2>"
            "<table class='grid'><thead><tr><th>Discount rate</th><th>DCF value</th></tr></thead>"
            f"<tbody>{srows}</tbody></table>"
        )

    edr = d.get("effective_discount_rate")
    cost_note_html = (
        f"<p class='note'>Income methods use an effective discount rate of "
        f"{_pct(edr, 100)} — {'public-company' if edr and edr <= 0.12 else 'small-business'} "
        f"cost of capital.</p>" if edr else ""
    )

    completion = d["diligence"].get("completion_pct")
    completion_chip = (
        f"<div class='chip'><div class='k'>Diligence</div><div class='v'>{_esc(completion)}% complete</div></div>"
        if completion is not None else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Valuation Report — {_esc(d['target_name'])}</title>
<style>
  :root {{ --accent:{ACCENT}; --accent2:{ACCENT2}; --light:{LIGHT}; --grey:{GREY}; }}
  * {{ box-sizing:border-box; }}
  body {{ font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; color:#1a1a1a;
         margin:0; padding:0; background:#fff; line-height:1.5; }}
  .wrap {{ max-width:820px; margin:0 auto; padding:40px 48px 64px; }}
  header {{ border-bottom:3px solid var(--accent); padding-bottom:16px; margin-bottom:8px; }}
  .brand {{ color:var(--accent); font-weight:700; letter-spacing:.5px; font-size:14px; }}
  h1 {{ font-size:28px; margin:6px 0 2px; color:#111; }}
  .meta {{ color:#666; font-size:13px; }}
  .hero {{ background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#fff;
          border-radius:12px; padding:24px 28px; margin:24px 0; }}
  .hero .label {{ text-transform:uppercase; letter-spacing:1px; font-size:12px; opacity:.85; }}
  .hero .range {{ font-size:34px; font-weight:700; margin-top:6px; }}
  .hero .mid {{ font-size:14px; opacity:.9; margin-top:4px; }}
  .chips {{ display:flex; gap:12px; flex-wrap:wrap; margin:18px 0 8px; }}
  .chip {{ background:var(--grey); border-radius:10px; padding:10px 14px; min-width:120px; }}
  .chip .k {{ font-size:11px; text-transform:uppercase; letter-spacing:.5px; color:#777; }}
  .chip .v {{ font-size:17px; font-weight:600; color:var(--accent); }}
  h2 {{ color:var(--accent2); font-size:18px; margin:28px 0 10px; }}
  h2 .sub, .sub {{ font-weight:400; font-size:13px; color:#888; }}
  table {{ width:100%; border-collapse:collapse; margin:6px 0 4px; font-size:14px; }}
  th, td {{ text-align:left; padding:9px 12px; border-bottom:1px solid #e3e3e3; }}
  thead th {{ background:var(--accent); color:#fff; font-weight:600; }}
  .grid thead th {{ background:var(--light); color:var(--accent); }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; font-weight:600; }}
  ul.flags {{ list-style:none; padding:0; margin:8px 0; }}
  ul.flags li {{ padding:8px 0; border-bottom:1px solid #eee; }}
  .badge {{ color:#fff; font-size:11px; font-weight:700; padding:2px 8px; border-radius:6px; margin-right:8px; }}
  .cat {{ display:inline-block; min-width:90px; color:#666; font-size:13px; margin-right:8px; }}
  .note {{ color:#999; font-size:12px; }}
  footer {{ margin-top:36px; padding-top:14px; border-top:1px solid #ddd; color:#888; font-size:12px; }}
  @media print {{ .wrap {{ padding:0; max-width:none; }} .hero {{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }} }}
</style></head>
<body><div class="wrap">
  <header>
    <div class="brand">DEALLENS</div>
    <h1>Valuation Report — {_esc(d['target_name'])}</h1>
    <div class="meta">{meta}</div>
  </header>

  <div class="hero">
    <div class="label">Recommended Value Range</div>
    <div class="range">{_money(rr.get('low'))} – {_money(rr.get('high'))}</div>
    <div class="mid">Midpoint {_money(rr.get('mid'))}</div>
  </div>

  <div class="chips">
    <div class="chip"><div class="k">Normalized EBITDA</div><div class="v">{_money(norm.get('normalized_ebitda'))}</div></div>
    <div class="chip"><div class="k">SDE</div><div class="v">{_money(norm.get('sde'))}</div></div>
    <div class="chip"><div class="k">Risk multiple cut</div><div class="v">{_pct(d['risk'].get('multiple_discount'),100)}</div></div>
    {completion_chip}
  </div>

  <h2>Valuation Approaches</h2>
  <table><thead><tr><th>Approach</th><th style="text-align:right">Result</th></tr></thead>
  <tbody>{approach_rows}</tbody></table>
  {cost_note_html}

  {comps_html}
  {flags_html}
  {sens_html}

  <footer>{_esc(d['disclaimer'])}</footer>
</div></body></html>"""


def render(result: Dict[str, Any], fmt: str = "html", options: Optional[Dict[str, Any]] = None) -> str:
    fmt = (fmt or "html").lower()
    options = options or {}
    # Plain-English 'investor' style — same data, non-finance explanations.
    if str(options.get("style", "")).lower() in ("plain", "investor"):
        from . import investor
        if fmt in ("markdown", "md"):
            return investor.build_investor_markdown(result, options)
        return investor.build_investor_html(result, options)
    if fmt in ("html", "htm"):
        return build_html(result, options)
    if fmt in ("markdown", "md"):
        return build_markdown(result, options)
    raise ValueError(f"unknown format {fmt!r}; use 'html' or 'markdown'")
