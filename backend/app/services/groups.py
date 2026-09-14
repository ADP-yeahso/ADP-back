"""Group invitation, membership, and cheer use cases."""

import secrets

from fastapi import HTTPException, status

from app.repositories import groups as repository

DEFAULT_PATIENT_NICKNAME = "환자"
DEFAULT_PATIENT_RELATION = "보호자"


def _invite_code() -> str:
    return secrets.token_urlsafe(8).upper()


def require_member(user_id: str, group_id: int) -> None:
    repository.get_group(group_id)
    if not repository.is_member(group_id, user_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not a group member")


def group_summary(group: dict) -> dict:
    return {**group, "member_count": repository.count_members(group["id"])}


def create_group(user_id: str, data: dict) -> dict:
    repository.ensure_user_profile(user_id)
    group = repository.create_group({**data, "invite_code": _invite_code()})
    repository.create_membership(
        user_id, group["id"], DEFAULT_PATIENT_NICKNAME, DEFAULT_PATIENT_RELATION
    )
    return group_summary(group)


def list_groups(user_id: str) -> list[dict]:
    return [group_summary(group) for group in repository.list_groups(user_id)]


def join_group(user_id: str, invite_code: str) -> dict:
    repository.ensure_user_profile(user_id)
    group = repository.get_group_by_invite_code(invite_code)
    if not repository.is_member(group["id"], user_id):
        repository.create_membership(
            user_id, group["id"], DEFAULT_PATIENT_NICKNAME, DEFAULT_PATIENT_RELATION
        )
    return group_summary(group)


def get_group_detail(user_id: str, group_id: int) -> dict:
    require_member(user_id, group_id)
    group = group_summary(repository.get_group(group_id))
    return {**group, "members": repository.get_members(group_id)}


def update_group(user_id: str, group_id: int, data: dict) -> dict:
    require_member(user_id, group_id)
    return group_summary(repository.update_group(group_id, data))


def list_members(user_id: str, group_id: int) -> list[dict]:
    require_member(user_id, group_id)
    return repository.get_members(group_id)


def update_my_membership(user_id: str, group_id: int, data: dict) -> dict:
    require_member(user_id, group_id)
    return repository.update_membership(group_id, user_id, data)


def leave_group(user_id: str, group_id: int) -> None:
    require_member(user_id, group_id)
    if repository.count_members(group_id) <= 1:
        raise HTTPException(status.HTTP_409_CONFLICT, "The last group member cannot leave")
    repository.delete_membership(group_id, user_id)


def send_cheer(sender_user_id: str, group_id: int, receiver_user_id: str) -> dict:
    require_member(sender_user_id, group_id)
    if sender_user_id == receiver_user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot cheer yourself")
    if not repository.is_member(group_id, receiver_user_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target group member not found")
    if repository.has_cheered_today(group_id, sender_user_id, receiver_user_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "You already cheered this member today")
    return repository.create_cheer(group_id, sender_user_id, receiver_user_id)
