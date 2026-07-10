"""Plain-English 'investor report' — explains a valuation to a non-finance reader.

Same input as the standard report (an orchestrator or valuation result), but the
output is written for someone with no finance background: what the number means,
what each method is really saying, what the risks mean *for a buyer*, what to do
about the asking price, and a short glossary. No jargon left unexplained.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from .normalize import extract

ACCENT = "#1F4E79"
ACCENT2 = "#2E75B6"


def _money(n: Optional[float]) -> str:
    if n is None:
        return "—"
    try:
        return f"${float(n):,.0f}"
    except (TypeError, ValueError):
        return str(n)


def _esc(s: Any) -> str:
    return html.escape(str(s if s is not None else ""))


# Plain-English explanations for common diligence red flags.
_RISK_PLAIN = [
    (["customer concentration", "top customer"],
     "A large share of sales comes from one or a few customers. If one leaves, "
     "revenue could drop sharply — so buyers pay less for that risk."),
    (["owner dependence", "owner-dependent", "owner is", "key relationship"],
     "The business leans heavily on the current owner (their relationships, "
     "know-how, or presence). It may lose customers or stumble once they leave."),
    (["supplier"],
     "The business depends on one or few suppliers. If a supplier raises prices or "
     "walks away, costs and reliability suffer."),
    (["declining revenue", "revenue trend"],
     "Sales are shrinking. Buyers pay less for a business heading the wrong way."),
    (["retention", "churn"],
     "Customers don't stick around as well as you'd want — you'd have to keep "
     "winning new ones just to stay flat."),
    (["litigation", "legal"],
     "There's a legal dispute. It could cost money or time, so it lowers value."),
    (["lease"],
     "The premises lease may not transfer to a new owner — you could lose the "
     "location, which for some businesses is everything."),
    (["books", "records"],
     "The financial records are messy or incomplete, so the numbers are less "
     "trustworthy until verified."),
    (["tax"],
     "There may be unpaid or unfiled taxes — a hidden liability you'd inherit."),
]


def _risk_plain(label: str) -> str:
    low = (label or "").lower()
    for keys, text in _RISK_PLAIN:
        if any(k in low for k in keys):
            return text
    return "Something worth investigating before you buy — ask the seller about it."


def _view(result: Dict[str, Any]) -> Dict[str, Any]:
    return extract(result)


def _sections(result: Dict[str, Any]) -> Dict[str, Any]:
    d = _view(result)
    rr = d["recommended_range"]
    ap = d["approaches"]
    norm = d["normalization"]
    risk = d["risk"]

    # Approach explanations present in the result.
    approach_lines: List[Dict[str, str]] = []
    if "income" in ap:
        inc = ap["income"]
        if inc.get("dcf"):
            approach_lines.append({
                "title": "Its future earnings (the thorough method)",
                "text": "We estimated the cash this business should produce in the years "
                        "ahead and converted that to what it's worth in today's money. "
                        f"This came out to about {_money(inc['dcf'].get('value'))}."})
        if inc.get("capitalization"):
            approach_lines.append({
                "title": "A simpler earnings check",
                "text": "A quicker version of the same idea — take the yearly profit and "
                        "scale it up — gave roughly "
                        f"{_money(inc['capitalization'].get('value'))}."})
    if "market" in ap:
        mk = ap["market"]
        approach_lines.append({
            "title": "What similar businesses sell for",
            "text": f"Comparable businesses typically sell for {mk.get('low_multiple')}–"
                    f"{mk.get('high_multiple')} times their {str(mk.get('metric','')).upper()} "
                    f"(a common earnings measure). Applied here, that's "
                    f"{_money(mk.get('low'))} to {_money(mk.get('high'))}."})
    if "asset" in ap:
        approach_lines.append({
            "title": "Its break-up value (a floor)",
            "text": "If you simply added up everything the business owns and subtracted "
                    "what it owes, you'd get "
                    f"{_money(ap['asset'].get('value'))}. Think of this as a floor — the "
                    "value of the 'stuff', ignoring the business's ability to earn."})

    flags = d["red_flags"]
    risks = [{"label": f.get("label", ""), "plain": _risk_plain(f.get("label", "")),
              "severity": str(f.get("severity", "")).lower()} for f in flags]

    return {
        "target": d["target_name"], "range": rr, "norm": norm,
        "risk_discount": risk.get("multiple_discount", 0),
        "approaches": approach_lines, "risks": risks,
        "completion": d["diligence"].get("completion_pct"),
        "overall_risk": d["diligence"].get("overall_risk_level"),
        "risk_profile": d["diligence"].get("risk_profile", []),
        "ai_findings": d["diligence"].get("ai_findings", []),
        "cost_note": _cost_of_capital_note(d.get("effective_discount_rate"), d.get("cost_of_capital")),
    }


def _cost_of_capital_note(edr, coc=None):
    """Plain-English explanation of the discount rate used. Classifies by the BASE
    cost of capital (the tier), then explains any diligence risk premium on top."""
    if not edr:
        return None
    eff = edr * 100
    base = (coc or {}).get("discount_rate")
    tier = (coc or {}).get("tier")
    base_pct = base * 100 if base else eff
    is_public = (tier == "public") if tier else base_pct <= 12
    kind = ("a large, stable, publicly-traded company, whose earnings are relatively "
            "predictable and so are discounted gently") if is_public else (
            "a smaller private business, which is riskier and harder to sell, so its future "
            "earnings are discounted more heavily")
    note = f"We discounted future earnings at a base rate of about {base_pct:.0f}% a year — the rate suited to {kind}."
    if eff - base_pct >= 0.4:
        note += (f" Due-diligence risks raised the effective rate to about {eff:.0f}%, which is "
                 "why the estimate is more conservative.")
    return note


def _diligence_lines(s: Dict[str, Any]) -> List[str]:
    """Plain-English summary of how far diligence has gone and where concerns are."""
    lines: List[str] = []
    comp = s.get("completion")
    if comp is not None:
        if comp <= 0:
            lines.append("The due-diligence checklist hasn't been filled in yet, so this is a "
                         "<em>preliminary</em> valuation — it reflects the financials but not a "
                         "verified investigation of the business. Working through the checklist "
                         "will make it far more reliable.")
        elif comp < 60:
            lines.append(f"About {comp:.0f}% of the due-diligence checklist is done. A lot is "
                         "still unchecked — and unknowns are themselves a risk. Verify more "
                         "before leaning on this number.")
        else:
            lines.append(f"About {comp:.0f}% of the due-diligence checklist is complete — a "
                         "reasonably thorough look. Still confirm the critical items marked ★.")
    findings = s.get("ai_findings") or []
    if findings:
        order = {"high": 3, "medium": 2, "low": 1}
        fs = sorted(findings, key=lambda f: -order.get(str(f.get("severity", "")).lower(), 0))
        lines.append("Reading the uploaded document, these points stood out to check — each is a "
                     "lead to confirm, not a proven fact. They already nudge the value down a "
                     "little; confirming them on the checklist applies their full weight:")
        # One line per finding (renderers wrap each as its own paragraph/bullet).
        for f in fs:
            lines.append(f"<em>{_esc(str(f.get('severity', '')).title())}</em> — "
                         f"{_esc(f.get('category', ''))}: {_esc(f.get('finding', ''))}")
    prof = [p for p in (s.get("risk_profile") or []) if p.get("level") not in (None, "none")]
    if prof:
        order = {"high": 3, "medium": 2, "low": 1}
        prof.sort(key=lambda p: -order.get(p.get("level"), 0))
        parts = "; ".join(f"{p['category']} ({p['level']} concern)" for p in prof)
        lines.append(f"Where concerns showed up by area: {parts}.")
    return lines


# ---------------------------------------------------------------------------
# Plain-English HTML fragments for the Bank and Conglomerate screens.
# (These return an injectable fragment, not a full page.)
# ---------------------------------------------------------------------------
_FRAG = ("border:1px solid #e2ebf5;background:#f5f8fc;border-radius:10px;"
         "padding:14px 18px;margin-top:14px;line-height:1.6;")


def build_investor_bank(result: Dict[str, Any]) -> str:
    ap = result.get("approaches", {}) or {}
    rr = result.get("recommended_range") or {}
    roe = result.get("roe")
    pb = ap.get("price_to_book"); pe = ap.get("price_to_earnings")
    parts = [f"<div style='{_FRAG}'>",
             "<div style='font-weight:700;color:%s'>In plain English</div>" % ACCENT,
             "<p>A bank isn't valued like a normal company — you can't just multiply its "
             "profit, because lending and borrowing money <em>is</em> its business "
             "(interest is its revenue, not a cost). So we look at two things:</p><ul>"]
    if pb:
        parts.append("<li><strong>Its net worth (book value).</strong> What the bank owns "
                     "minus what it owes, times a multiple. Banks often trade near this "
                     f"— here that's {_money(pb.get('low'))} to {_money(pb.get('high'))}.</li>")
    if pe:
        parts.append("<li><strong>Its yearly profit.</strong> Profit times a multiple — here "
                     f"{_money(pe.get('low'))} to {_money(pe.get('high'))}.</li>")
    parts.append("</ul>")
    if rr:
        parts.append(f"<p>Blending those, it looks worth roughly <strong>{_money(rr.get('low'))} "
                     f"to {_money(rr.get('high'))}</strong>.</p>")
    if roe is not None:
        parts.append(f"<p>Its <strong>return on equity is {roe*100:.1f}%</strong> — how much "
                     "profit it earns on its net worth each year. Higher is generally healthier; "
                     "many solid banks sit around 10–15%.</p>")
    parts.append("<p><strong>For you as a buyer:</strong> a price within that range is broadly "
                 "fair. Well below book value can mean a bargain — or that the market worries "
                 "about the loans on its books. Always dig into loan quality.</p>")
    parts.append("<div style='color:#888;font-size:12px;margin-top:6px'>A guide to help you think, "
                 "not financial advice.</div></div>")
    return "".join(parts)


def build_investor_sotp(result: Dict[str, Any]) -> str:
    segs = result.get("segments", []) or []
    eq = result.get("equity_range") or {}
    disc = result.get("conglomerate_discount", 0)
    parts = [f"<div style='{_FRAG}'>",
             "<div style='font-weight:700;color:%s'>In plain English</div>" % ACCENT,
             "<p>This company is really several different businesses bundled together. Each one "
             "is worth a different amount per dollar of earnings, so we valued them "
             "<strong>separately</strong> and added them up — that's 'sum of the parts'.</p><ul>"]
    for s in segs:
        v = s.get("value_range", {})
        parts.append(f"<li><strong>{_esc(s.get('name'))}</strong> looks worth about "
                     f"{_money(v.get('low'))} to {_money(v.get('high'))}.</li>")
    parts.append("</ul>")
    if eq:
        note = f" (after a {disc*100:.0f}% conglomerate discount and subtracting debt)" if disc else ""
        parts.append(f"<p>Added together{note}, the whole company looks worth roughly "
                     f"<strong>{_money(eq.get('low'))} to {_money(eq.get('high'))}</strong>.</p>")
    parts.append("<p><strong>Why value the parts separately?</strong> A single blended multiple "
                 "would ignore that, say, a fast-growing software unit is worth far more per "
                 "dollar than a low-margin retail unit. Splitting it up is more honest.</p>")
    parts.append("<div style='color:#888;font-size:12px;margin-top:6px'>A guide to help you think, "
                 "not financial advice.</div></div>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------
def build_investor_markdown(result: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> str:
    s = _sections(result)
    rr = s["range"]
    L: List[str] = []
    L.append(f"# Plain-English Valuation — {s['target']}")
    L.append("")
    L.append("_A guide to what this business appears to be worth and what it means "
             "if you're thinking of buying it. No finance background needed._")
    L.append("")
    L.append("## What it looks worth")
    if rr:
        L.append(f"Our best estimate is that **{s['target']}** is worth somewhere between "
                 f"**{_money(rr.get('low'))}** and **{_money(rr.get('high'))}**, with a "
                 f"middle estimate of **{_money(rr.get('mid'))}**.")
        L.append("")
        L.append("Treat this as a *fair-price zone*, not one exact figure. Every valuation "
                 "is a range, because it depends on assumptions about the future.")
    else:
        L.append("We couldn't produce a reliable range from the numbers given — usually a "
                 "sign the business is losing money or the inputs are incomplete.")
    L.append("")
    L.append("## How we got there — checking it three ways")
    L.append("We valued it a few different ways and blended them. When the methods roughly "
             "agree, you can be more confident.")
    L.append("")
    for a in s["approaches"]:
        L.append(f"- **{a['title']}.** {a['text']}")
    L.append("")
    if s.get("cost_note"):
        L.append(f"_{s['cost_note']}_")
        L.append("")
    dl = _diligence_lines(s)
    if dl:
        L.append("## How thoroughly it's been checked")
        for line in dl:
            L.append(line.replace("<em>", "*").replace("</em>", "*"))
        L.append("")
    L.append("## What to watch out for")
    if s["risks"]:
        if s["risk_discount"]:
            L.append(f"These concerns lowered the estimated value by about "
                     f"**{s['risk_discount']*100:.0f}%**:")
            L.append("")
        for r in s["risks"]:
            L.append(f"- **{r['label']}** — {r['plain']}")
    else:
        L.append("No major red flags were entered. Note: that may just mean the diligence "
                 "checklist wasn't filled in — it's worth doing before you rely on this.")
    L.append("")
    L.append("## What this means for you as a buyer")
    if rr:
        L.append(f"- If the seller is asking **within {_money(rr.get('low'))}–"
                 f"{_money(rr.get('high'))}**, the price is broadly in line with what the "
                 "business looks worth.")
        L.append(f"- **Above {_money(rr.get('high'))}** — you'd be paying a premium. Make "
                 "sure you understand what justifies it (fast growth? a strong brand? loyal, "
                 "locked-in customers?).")
        L.append(f"- **Below {_money(rr.get('low'))}** — it may be a bargain, *or* a sign "
                 "something's wrong. Worth investigating why it's cheap.")
    L.append("")
    L.append("**Questions worth asking the seller:** Why are you selling? How much does the "
             "business depend on you personally? Will the customers and contracts stay after "
             "the sale? Are the financials clean and independently verified?")
    L.append("")
    L.append("## A few terms, briefly")
    L.append("- **SDE / EBITDA** — measures of yearly profit (roughly, the cash the business "
             "throws off before financing and tax quirks).")
    L.append("- **Multiple** — how many years' worth of profit a buyer pays (a '3× multiple' "
             "means paying three times yearly earnings).")
    L.append("- **DCF** — valuing a business by the future cash it will generate.")
    L.append("- **Net asset value** — what you'd have left if you sold everything it owns and "
             "paid off what it owes.")
    L.append("")
    L.append("---")
    L.append("_This is a guide to help you think, not financial or legal advice. Before "
             "buying, have an accountant and a lawyer review everything._")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
def build_investor_html(result: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> str:
    s = _sections(result)
    rr = s["range"]

    approach_html = "".join(
        f"<div class='card'><div class='ctitle'>{_esc(a['title'])}</div>"
        f"<div>{_esc(a['text'])}</div></div>" for a in s["approaches"])

    if s["risks"]:
        intro = (f"<p>These concerns lowered the estimated value by about "
                 f"<strong>{s['risk_discount']*100:.0f}%</strong>:</p>") if s["risk_discount"] else ""
        risk_html = intro + "<ul class='risks'>" + "".join(
            f"<li><strong>{_esc(r['label'])}</strong> — {_esc(r['plain'])}</li>"
            for r in s["risks"]) + "</ul>"
    else:
        risk_html = ("<p>No major red flags were entered. Note: that may just mean the "
                     "diligence checklist wasn't filled in — worth doing before you rely on this.</p>")

    cost_html = f"<p class='note'>{_esc(s['cost_note'])}</p>" if s.get("cost_note") else ""

    dl = _diligence_lines(s)
    dilig_html = ""
    if dl:
        dilig_html = ("<h2>How thoroughly it's been checked</h2>"
                      + "".join(f"<p>{line}</p>" for line in dl))

    if rr:
        hero = (f"<div class='rng'>{_money(rr.get('low'))} – {_money(rr.get('high'))}</div>"
                f"<div class='mid'>middle estimate {_money(rr.get('mid'))}</div>")
        buyer = (
            f"<li>Asking <strong>within {_money(rr.get('low'))}–{_money(rr.get('high'))}</strong> "
            "— broadly in line with what it looks worth.</li>"
            f"<li>Asking <strong>above {_money(rr.get('high'))}</strong> — you're paying a "
            "premium; understand what justifies it (growth, brand, loyal customers).</li>"
            f"<li>Asking <strong>below {_money(rr.get('low'))}</strong> — possibly a bargain, "
            "or a warning sign worth investigating.</li>")
    else:
        hero = "<div class='rng'>No reliable range</div><div class='mid'>likely loss-making or incomplete inputs</div>"
        buyer = "<li>Get the numbers verified before considering an offer.</li>"

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Plain-English Valuation — {_esc(s['target'])}</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1a2230;margin:0;background:#fff;line-height:1.6;}}
 .wrap{{max-width:760px;margin:0 auto;padding:40px 44px 64px;}}
 .brand{{color:{ACCENT};font-weight:700;letter-spacing:.5px;font-size:13px;}}
 h1{{font-size:26px;margin:6px 0 2px;}}
 .lead{{color:#556;font-style:italic;margin-bottom:8px;}}
 h2{{color:{ACCENT2};font-size:19px;margin:30px 0 10px;}}
 .hero{{background:linear-gradient(135deg,{ACCENT},{ACCENT2});color:#fff;border-radius:12px;padding:22px 26px;margin:16px 0;}}
 .hero .lbl{{text-transform:uppercase;letter-spacing:1px;font-size:11px;opacity:.85;}}
 .hero .rng{{font-size:30px;font-weight:700;margin-top:4px;}}
 .hero .mid{{font-size:13px;opacity:.9;}}
 .card{{background:#f5f8fc;border:1px solid #e2ebf5;border-radius:10px;padding:12px 16px;margin:8px 0;}}
 .card .ctitle{{font-weight:700;color:{ACCENT};margin-bottom:2px;}}
 ul.risks li, .buyer li{{margin:7px 0;}}
 .note{{background:#fff8e1;border:1px solid #f0e0a0;border-radius:10px;padding:12px 16px;margin-top:10px;}}
 footer{{margin-top:34px;padding-top:14px;border-top:1px solid #ddd;color:#888;font-size:12px;}}
 @media print{{.wrap{{padding:0;}} .hero{{-webkit-print-color-adjust:exact;print-color-adjust:exact;}}}}
</style></head><body><div class="wrap">
 <div class="brand">DEALLENS · PLAIN-ENGLISH REPORT</div>
 <h1>What is {_esc(s['target'])} worth?</h1>
 <div class="lead">A guide for a buyer with no finance background — what the number means and what to do about it.</div>

 <div class="hero"><div class="lbl">What it looks worth</div>{hero}</div>
 <p>Treat this as a <strong>fair-price zone</strong>, not one exact figure. Every valuation is a
 range because it depends on assumptions about the future.</p>

 <h2>How we checked it</h2>
 <p>We valued the business a few different ways and blended them. When the methods roughly agree,
 you can be more confident in the answer.</p>
 {approach_html}
 {cost_html}

 {dilig_html}

 <h2>What to watch out for</h2>
 {risk_html}

 <h2>What this means for you as a buyer</h2>
 <ul class="buyer">{buyer}</ul>
 <div class="note"><strong>Questions worth asking the seller:</strong> Why are you selling? How
 much does the business depend on you personally? Will customers and contracts stay after the
 sale? Are the financials clean and independently verified?</div>

 <h2>A few terms, briefly</h2>
 <ul>
  <li><strong>SDE / EBITDA</strong> — measures of yearly profit (roughly, the cash the business
  throws off before financing and tax quirks).</li>
  <li><strong>Multiple</strong> — how many years' worth of profit a buyer pays (a "3×" means
  paying three times yearly earnings).</li>
  <li><strong>DCF</strong> — valuing a business by the future cash it will generate.</li>
  <li><strong>Net asset value</strong> — what's left if you sold everything it owns and paid off
  what it owes.</li>
 </ul>

 <footer>This is a guide to help you think, not financial or legal advice. Before buying, have an
 accountant and a lawyer review everything.</footer>
</div></body></html>"""
