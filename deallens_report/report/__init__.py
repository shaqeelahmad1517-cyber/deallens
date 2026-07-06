"""DealLens report primitive — render a deal evaluation into a client-ready report."""
from .docx_writer import available as docx_available, write_docx
from .normalize import extract
from .primitive import ENGINE_NAME, ENGINE_VERSION, MANIFEST, invoke, manifest
from .investor import build_investor_html, build_investor_markdown
from .render import build_html, build_markdown, render

__version__ = ENGINE_VERSION
__all__ = [
    "render", "build_html", "build_markdown", "extract",
    "write_docx", "docx_available",
    "invoke", "manifest", "MANIFEST", "ENGINE_NAME", "ENGINE_VERSION",
]
