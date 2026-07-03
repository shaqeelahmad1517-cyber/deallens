"""Format readers: file -> rows (or text). CSV and XLSX use only the stdlib.

- CSV/TSV  : csv module
- XLSX     : zipfile + xml (a .xlsx is a zip of XML) — no openpyxl needed
- TXT      : read as text
- PDF      : optional (pdfplumber or pypdf if installed); otherwise a clear error
"""
from __future__ import annotations

import csv
import io
import os
import re
import xml.etree.ElementTree as ET
import zipfile
from typing import Any, List, Tuple


def read_csv(path_or_text: str, is_text: bool = False) -> List[List[str]]:
    if is_text:
        f = io.StringIO(path_or_text)
    else:
        f = open(path_or_text, "r", encoding="utf-8-sig", newline="")
    try:
        sample = f.read(2048)
        f.seek(0)
        delim = "\t" if "\t" in sample and sample.count("\t") >= sample.count(",") else ","
        return [list(row) for row in csv.reader(f, delimiter=delim)]
    finally:
        if not is_text:
            f.close()


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref or "A").group(0)
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def read_xlsx(path: str) -> List[List[Any]]:
    """Minimal XLSX reader (first worksheet) using only the standard library."""
    with zipfile.ZipFile(path) as z:
        shared: List[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root:
                text = "".join(t.text or "" for t in si.iter() if _strip_ns(t.tag) == "t")
                shared.append(text)
        # find first worksheet
        sheets = sorted(n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
        if not sheets:
            return []
        root = ET.fromstring(z.read(sheets[0]))
        rows: List[List[Any]] = []
        for row_el in root.iter():
            if _strip_ns(row_el.tag) != "row":
                continue
            cells: List[Any] = []
            auto_idx = 0
            for c in row_el:
                if _strip_ns(c.tag) != "c":
                    continue
                ref = c.attrib.get("r", "")
                ctype = c.attrib.get("t", "")
                vtext = ""
                for child in c:
                    tag = _strip_ns(child.tag)
                    if tag == "v":
                        vtext = child.text or ""
                        break
                    if tag == "is":  # inline string: <is><t>...</t></is>
                        vtext = "".join(t.text or "" for t in child.iter() if _strip_ns(t.tag) == "t")
                        break
                    if tag == "t":
                        vtext = child.text or ""
                        break
                if ctype == "s" and vtext.isdigit():
                    vtext = shared[int(vtext)] if int(vtext) < len(shared) else ""
                # Use the cell reference for column alignment; fall back to
                # positional order if the exporter omitted the 'r' attribute
                # (otherwise every cell would collapse to column 0).
                idx = _col_index(ref) if ref else auto_idx
                auto_idx = idx + 1
                while len(cells) <= idx:
                    cells.append("")
                cells[idx] = vtext
            rows.append(cells)
        return rows


def read_pdf_text(path: str) -> str:
    """Extract text from a PDF using pdfplumber or pypdf if available."""
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return "\n".join((pg.extract_text() or "") for pg in pdf.pages)
    except ImportError:
        pass
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        return "\n".join((pg.extract_text() or "") for pg in reader.pages)
    except ImportError:
        pass
    raise RuntimeError(
        "PDF support needs an extra library. Install one with "
        "'pip install pdfplumber' (or 'pip install pypdf'), or export the "
        "statement to CSV/Excel, or paste the text directly."
    )


def read_docx(path: str) -> List[List[Any]]:
    """Read a .docx into rows: table rows become cell lists; paragraphs become
    single-cell rows. Pure stdlib (a .docx is a zip of XML)."""
    with zipfile.ZipFile(path) as z:
        if "word/document.xml" not in z.namelist():
            return []
        root = ET.fromstring(z.read("word/document.xml"))

    def para_text(p) -> str:
        parts = []
        for el in p.iter():
            tag = _strip_ns(el.tag)
            if tag == "t":
                parts.append(el.text or "")
            elif tag == "tab":
                parts.append(" ")
        return "".join(parts).strip()

    def table_rows(tbl) -> List[List[str]]:
        out = []
        for tr in tbl:
            if _strip_ns(tr.tag) != "tr":
                continue
            cells = []
            for tc in tr:
                if _strip_ns(tc.tag) != "tc":
                    continue
                cells.append("".join(t.text or "" for t in tc.iter() if _strip_ns(t.tag) == "t").strip())
            if cells:
                out.append(cells)
        return out

    body = next((el for el in root if _strip_ns(el.tag) == "body"), root)
    rows: List[List[Any]] = []
    for child in body:
        tag = _strip_ns(child.tag)
        if tag == "p":
            txt = para_text(child)
            if txt:
                rows.append([txt])
        elif tag == "tbl":
            rows.extend(table_rows(child))
    return rows


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def read_file(path: str) -> Tuple[str, Any]:
    """Dispatch by extension. Returns ('rows', rows) or ('text', text)."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".csv", ".tsv"):
        return "rows", read_csv(path)
    if ext == ".xlsx":
        return "rows", read_xlsx(path)
    if ext == ".docx":
        return "rows", read_docx(path)
    if ext == ".pdf":
        return "text", read_pdf_text(path)
    if ext in (".txt", ".md", ""):
        return "text", read_text(path)
    raise ValueError(f"unsupported file type {ext!r}; use csv, xlsx, docx, pdf, or txt")
