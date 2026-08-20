from fastapi import APIRouter, Depends

from app.core.security import get_current_user_id

router = APIRouter()


@router.get("/me", tags=["users"])
def get_me(user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
	return {"id": user_id}
