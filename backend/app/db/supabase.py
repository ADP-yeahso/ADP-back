from supabase import Client, create_client

from app.core.config import get_settings


def get_supabase_client() -> Client | None:
    """Return an isolated service-role client for the current operation.

    Supabase auth methods such as ``sign_in_with_password`` mutate a client's
    in-memory session. Caching a shared client would therefore make a later
    repository query run with the previous user's access token instead of the
    configured service key.
    """
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
