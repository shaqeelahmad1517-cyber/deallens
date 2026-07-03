"""DealLens assist — rule-based add-back suggestions and narrative drafting."""
from .adjustments import suggest_adjustments
from .narrative import draft_narrative
from .primitive import ENGINE_NAME, ENGINE_VERSION, MANIFEST, invoke, manifest

__version__ = ENGINE_VERSION
__all__ = [
    "suggest_adjustments", "draft_narrative",
    "invoke", "manifest", "MANIFEST", "ENGINE_NAME", "ENGINE_VERSION",
]
