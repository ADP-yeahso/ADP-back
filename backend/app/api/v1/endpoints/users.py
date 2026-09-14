from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import AuthenticatedUser, get_current_user
from app.db.supabase import get_supabase_client
from app.schemas.users import UserProfileResponse, UserProfileUpsert

router = APIRouter()


@router.get("/me", tags=["users"])
def get_me(current_user: AuthenticatedUser = Depends(get_current_user)) -> UserProfileResponse:
	client = get_supabase_client()
	if client is None:
		raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase is not configured")

	result = client.table("users").select("*").eq("id", str(current_user.id)).execute()
	if not result.data:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found")
	return UserProfileResponse.model_validate(result.data[0])


@router.put("/me", tags=["users"])
def upsert_me(
	profile: UserProfileUpsert,
	current_user: AuthenticatedUser = Depends(get_current_user),
) -> UserProfileResponse:
	client = get_supabase_client()
	if client is None:
		raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase is not configured")
	if not current_user.email:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Authenticated user has no email")

	data = {
		"id": str(current_user.id),
		"email": current_user.email,
		**profile.model_dump(),
	}
	result = client.table("users").upsert(data, on_conflict="id").execute()
	if not result.data:
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User profile was not saved")
	return UserProfileResponse.model_validate(result.data[0])
