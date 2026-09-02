"""User profile persistence."""

from typing import Any

from fastapi import HTTPException

from app.db.supabase import get_supabase_client


def sign_up_with_email_password(email: str, password: str, name: str, phone_number: str) -> dict[str, Any]:
    client = get_supabase_client()
    if client is None:
        raise HTTPException(status_code=500, detail="Supabase client is not configured")

    try:
        result = client.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "name": name,
                        "phone_number": phone_number,
                    }
                },
            }
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=400, detail="User registration failed") from exc

    if not getattr(result, "user", None):
        raise HTTPException(status_code=400, detail="User registration failed")

    return {
        "user": {
            "id": result.user.id,
            "email": getattr(result.user, "email", None),
            "name": getattr(result.user, "user_metadata", {}).get("name") or name,
        }
    }


def sign_in_with_email_password(email: str, password: str) -> dict[str, Any]:
    client = get_supabase_client()
    if client is None:
        raise HTTPException(status_code=500, detail="Supabase client is not configured")

    try:
        result = client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=401, detail="Invalid email or password") from exc

    if not getattr(result, "user", None) or not getattr(result, "session", None):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
    }
