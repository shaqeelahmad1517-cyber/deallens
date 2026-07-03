"""DealLens UI — a zero-dependency local web app over the workspace primitive."""
from .server import handle_api, run

__all__ = ["run", "handle_api"]
