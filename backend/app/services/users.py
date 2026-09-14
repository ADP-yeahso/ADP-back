"""User profile use cases."""

from typing import Any

from app.repositories.users import sign_in_with_email_password, sign_up_with_email_password


def signup_user(email: str, password: str, name: str, phone_number: str) -> dict[str, Any]:
    return sign_up_with_email_password(
        email=email,
        password=password,
        name=name,
        phone_number=phone_number,
    )


def login_user(email: str, password: str) -> dict[str, Any]:
    return sign_in_with_email_password(email=email, password=password)
