"""Document ingestion engine: file / text / rows -> extracted financials."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import extract, readers

ENGINE_NAME = "deallens.documents"
ENGINE_VERSION = "1.0.0"


def ingest(path: Optional[str] = None, text: Optional[str] = None,
           rows: Optional[List[List[Any]]] = None,
           csv_text: Optional[str] = None) -> Dict[str, Any]:
    """Extract a financials block from one of: rows, text, csv_text, or a file path."""
    if rows is not None:
        result = extract.extract_from_rows(rows)
        source = "rows"
    elif csv_text is not None:
        result = extract.extract_from_rows(readers.read_csv(csv_text, is_text=True))
        source = "csv_text"
    elif text is not None:
        result = extract.extract_from_text(text)
        source = "text"
    elif path is not None:
        kind, data = readers.read_file(path)
        result = extract.extract_from_rows(data) if kind == "rows" else extract.extract_from_text(data)
        source = f"file:{path}"
    else:
        raise ValueError("provide one of: rows, text, csv_text, or path")

    result["engine"] = ENGINE_NAME
    result["version"] = ENGINE_VERSION
    result["source"] = source
    result["disclaimer"] = (
        "Auto-extracted — review every figure before use. Best-effort label "
        "matching, not a substitute for reading the statements."
    )
    return result
