from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.supabase import get_supabase_client

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_id(
	credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UUID:
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
		return UUID(user_id)
	except Exception as exc:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid or expired access token",
			headers={"WWW-Authenticate": "Bearer"},
		) from exc
