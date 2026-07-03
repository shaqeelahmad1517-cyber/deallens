"""DealLens documents — extract financials from statements (CSV/Excel/PDF/text)."""
from .engine import ENGINE_NAME, ENGINE_VERSION, ingest
from .extract import extract_from_pairs, extract_from_rows, extract_from_text, parse_number
from .primitive import MANIFEST, invoke, manifest

__version__ = ENGINE_VERSION
__all__ = [
    "ingest", "invoke", "manifest", "MANIFEST", "ENGINE_NAME", "ENGINE_VERSION",
    "extract_from_rows", "extract_from_text", "extract_from_pairs", "parse_number",
]
