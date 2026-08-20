from uuid import UUID
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.supabase import get_supabase_client

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
	id: UUID
	email: str | None


async def get_current_user(
	credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
	if credentials is None or credentials.scheme.lower() != "bearer":
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Bearer access token is required",
			headers={"WWW-Authenticate": "Bearer"},
		)

	client = get_supabase_client()
	if client is None:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="Supabase authentication is not configured",
		)

	try:
		response = client.auth.get_user(credentials.credentials)
		user_id = response.user.id if response.user else None
		if not user_id:
			raise ValueError("Supabase returned no user")
		return AuthenticatedUser(id=UUID(user_id), email=response.user.email)
	except Exception as exc:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid or expired access token",
			headers={"WWW-Authenticate": "Bearer"},
		) from exc


async def get_current_user_id(
	current_user: AuthenticatedUser = Depends(get_current_user),
) -> UUID:
	return current_user.id
