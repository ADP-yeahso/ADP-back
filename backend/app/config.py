"""Backward-compatible settings imports.

New code should import from :mod:`app.core.config`.
"""

from app.core.config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
