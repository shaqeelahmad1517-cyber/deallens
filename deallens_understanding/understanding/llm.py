"""LLM transport for document understanding.

A *transport* is any callable ``transport(prompt: str) -> dict`` that returns the
parsed JSON the model produced. This module ships one real transport (Anthropic
or OpenAI, chosen by env) built on the standard library only — no SDK to install.
Tests inject a mock transport instead of hitting the network.

Configuration (all via environment, so the key never lives in code):
  DEALLENS_LLM_PROVIDER   "anthropic" (default) | "openai"
  ANTHROPIC_API_KEY / OPENAI_API_KEY
  DEALLENS_LLM_MODEL      overrides the per-provider default
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any, Dict, Optional

# Fields the model is asked to return. Kept aligned with the documents extractor
# (financials) and the diligence engine's auto-flag signals (signals).
_MAX_CHARS = 120_000  # ~30k tokens; long enough for a full annual report section

_INSTRUCTION = """You are a meticulous financial due-diligence analyst. Read the \
company document below and extract structured facts. Return ONLY a JSON object \
(no prose, no markdown fences) with exactly this shape:

{
  "company_name": string|null,
  "sector": string|null,
  "reporting_scale": "units" | "thousands" | "millions" | "billions",
  "financials": {
    "revenue": number|null, "net_income": number|null, "interest": number|null,
    "taxes": number|null, "depreciation": number|null, "amortization": number|null,
    "owner_compensation": number|null, "total_assets": number|null,
    "total_liabilities": number|null
  },
  "signals": {
    "top_customer_pct": number|null, "owner_dependent": true|false|null,
    "revenue_trend": "growing"|"flat"|"declining"|null, "clean_books": true|false|null,
    "litigation_pending": true|false|null, "contracts_assignable": true|false|null,
    "taxes_current": true|false|null
  },
  "findings": [
    {"category": string, "finding": string, "severity": "low"|"medium"|"high"}
  ]
}

Rules:
- "company_name": the subject company's name if stated (else null). "sector": the \
most specific industry label, lowercase, e.g. "consumer staples", "packaged food", \
"beverages", "consumer discretionary", "saas", "retail", "restaurant", "healthcare", \
"pharmaceuticals", "logistics", "manufacturing", "energy", "utilities", "telecom", \
"media", "real estate", "automotive", "aerospace and defense", "financial", "insurance". \
Prefer the precise category (a cereal/snack maker is "packaged food"/"consumer staples", \
not just "manufacturing"). Use null only if truly unclear.
- Report every financial figure EXACTLY as printed in the statement. Do NOT \
multiply, scale, or add zeros yourself. Instead set "reporting_scale" to the unit \
the statement is presented in — look for wording like "in millions" / "in \
thousands" near the statement header (use "units" if figures are already whole \
dollars). We apply the multiplier ourselves.
- Use the most recent reported period. Use null for anything not stated — never guess.
- "findings" are diligence red/amber flags a buyer should verify: customer or \
supplier concentration, going-concern or material-weakness language, litigation, \
declining margins, related-party dealings, debt covenants, key-person risk, etc.
- Keep each finding to one sentence. Return [] if nothing notable.

DOCUMENT:
"""


def build_prompt(text: str) -> str:
    """Assemble the extraction prompt, truncating very long documents."""
    doc = text or ""
    truncated = len(doc) > _MAX_CHARS
    if truncated:
        doc = doc[:_MAX_CHARS] + "\n[...document truncated for length...]"
    return _INSTRUCTION + doc


def provider() -> str:
    return (os.environ.get("DEALLENS_LLM_PROVIDER") or "anthropic").strip().lower()


def _api_key() -> Optional[str]:
    if provider() == "openai":
        return os.environ.get("OPENAI_API_KEY")
    return os.environ.get("ANTHROPIC_API_KEY")


def available() -> bool:
    """True when an API key is configured for the selected provider."""
    return bool(_api_key())


def model_name() -> str:
    if os.environ.get("DEALLENS_LLM_MODEL"):
        return os.environ["DEALLENS_LLM_MODEL"]
    # Current-generation defaults; override per-account with DEALLENS_LLM_MODEL.
    return "gpt-4o-mini" if provider() == "openai" else "claude-haiku-4-5-20251001"


def extract_json(raw: str) -> Dict[str, Any]:
    """Pull a JSON object out of a model reply (tolerates ```json fences/prose)."""
    if not raw:
        raise ValueError("empty model response")
    s = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.S)
    if fence:
        s = fence.group(1)
    else:
        start, end = s.find("{"), s.rfind("}")
        if start != -1 and end != -1 and end > start:
            s = s[start:end + 1]
    return json.loads(s)


# --- real network transports (not exercised in tests) ----------------------
def _post_json(url: str, headers: Dict[str, str], body: Dict[str, Any],
               timeout: int = 60) -> Dict[str, Any]:  # pragma: no cover - network
    import urllib.error
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        # Surface the provider's actual error (bad key, unknown model, billing,
        # rate limit) instead of an opaque "HTTPError".
        try:
            detail = e.read().decode("utf-8", "replace")
        except Exception:
            detail = ""
        host = url.split("//", 1)[-1].split("/", 1)[0]
        raise RuntimeError(f"HTTP {e.code} from {host} (model '{model_name()}'): "
                           f"{detail[:400]}") from None


def _anthropic(prompt: str) -> Dict[str, Any]:  # pragma: no cover - network
    key = os.environ["ANTHROPIC_API_KEY"]
    out = _post_json(
        "https://api.anthropic.com/v1/messages",
        {"x-api-key": key, "anthropic-version": "2023-06-01",
         "content-type": "application/json"},
        {"model": model_name(), "max_tokens": 2000, "temperature": 0,
         "messages": [{"role": "user", "content": prompt}]},
    )
    text = "".join(block.get("text", "") for block in out.get("content", []))
    return extract_json(text)


def _openai(prompt: str) -> Dict[str, Any]:  # pragma: no cover - network
    key = os.environ["OPENAI_API_KEY"]
    out = _post_json(
        "https://api.openai.com/v1/chat/completions",
        {"Authorization": f"Bearer {key}", "content-type": "application/json"},
        {"model": model_name(), "temperature": 0,
         "response_format": {"type": "json_object"},
         "messages": [{"role": "user", "content": prompt}]},
    )
    text = out["choices"][0]["message"]["content"]
    return extract_json(text)


def real_transport(prompt: str) -> Dict[str, Any]:  # pragma: no cover - network
    """Call the configured provider. Raises if no key / provider unknown."""
    if not available():
        raise RuntimeError("no LLM API key configured")
    return _openai(prompt) if provider() == "openai" else _anthropic(prompt)
