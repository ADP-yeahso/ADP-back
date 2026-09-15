from fastapi import APIRouter, Depends, Response, status

from app.core.security import AuthenticatedUser, get_current_user
from app.schemas.groups import (
    CheerCreated,
    GroupCreate,
    GroupDetail,
    GroupJoin,
    GroupMember,
    GroupMemberUpdate,
    GroupSummary,
    GroupUpdate,
)
from app.services import groups as service

router = APIRouter()


def user_id(current_user: AuthenticatedUser) -> str:
    return str(current_user.id)


@router.post("", response_model=GroupSummary, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate, current_user: AuthenticatedUser = Depends(get_current_user)
):
    return service.create_group(user_id(current_user), payload.model_dump(mode="json"))


@router.get("", response_model=list[GroupSummary])
def list_groups(current_user: AuthenticatedUser = Depends(get_current_user)):
    return service.list_groups(user_id(current_user))


@router.post("/join", response_model=GroupSummary)
def join_group(payload: GroupJoin, current_user: AuthenticatedUser = Depends(get_current_user)):
    return service.join_group(user_id(current_user), payload.invite_code)


@router.get("/{group_id}", response_model=GroupDetail)
def get_group(group_id: int, current_user: AuthenticatedUser = Depends(get_current_user)):
    return service.get_group_detail(user_id(current_user), group_id)


@router.patch("/{group_id}", response_model=GroupSummary)
def update_group(
    group_id: int, payload: GroupUpdate, current_user: AuthenticatedUser = Depends(get_current_user)
):
    data = payload.model_dump(mode="json", exclude_unset=True)
    return service.update_group(user_id(current_user), group_id, data)


@router.get("/{group_id}/members", response_model=list[GroupMember])
def list_members(group_id: int, current_user: AuthenticatedUser = Depends(get_current_user)):
    return service.list_members(user_id(current_user), group_id)


@router.patch("/{group_id}/members/me", response_model=GroupMember)
def update_my_membership(
    group_id: int,
    payload: GroupMemberUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    data = payload.model_dump(mode="json", exclude_unset=True)
    return service.update_my_membership(user_id(current_user), group_id, data)


@router.delete("/{group_id}/members/me", status_code=status.HTTP_204_NO_CONTENT)
def leave_group(
    group_id: int, current_user: AuthenticatedUser = Depends(get_current_user)
) -> Response:
    service.leave_group(user_id(current_user), group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{group_id}/members/{member_user_id}/cheers",
    response_model=CheerCreated,
    status_code=status.HTTP_201_CREATED,
)
def send_cheer(
    group_id: int,
    member_user_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return service.send_cheer(user_id(current_user), group_id, member_user_id)
