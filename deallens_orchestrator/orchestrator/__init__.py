"""DealLens orchestrator — single-call deal evaluation over the three primitives."""
from .engine import ENGINE_NAME, ENGINE_VERSION, Orchestrator, run
from .primitive import MANIFEST, invoke, manifest

__version__ = ENGINE_VERSION
__all__ = [
    "run", "Orchestrator", "ENGINE_NAME", "ENGINE_VERSION",
    "invoke", "manifest", "MANIFEST",
]
