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
    }


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
