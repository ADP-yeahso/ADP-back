"""Backward-compatible Supabase client import.

New code should import from :mod:`app.db.supabase`.
"""

from app.db.supabase import get_supabase_client

__all__ = ["get_supabase_client"]
