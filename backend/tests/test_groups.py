from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.services import groups


def test_create_group_adds_creator_as_member(monkeypatch) -> None:
    membership = {}
    monkeypatch.setattr(groups, "_invite_code", lambda: "INVITE01")
    monkeypatch.setattr(groups.repository, "ensure_user_profile", lambda user_id: None)
    monkeypatch.setattr(
        groups.repository,
        "create_group",
        lambda data: {"id": 7, "created_at": datetime.now(timezone.utc), **data},
    )
    monkeypatch.setattr(
        groups.repository,
        "create_membership",
        lambda user_id, group_id, nickname, relation: membership.update(
            user_id=user_id, group_id=group_id, nickname=nickname, relation=relation
        ),
    )
    monkeypatch.setattr(groups.repository, "count_members", lambda group_id: 1)

    result = groups.create_group(
        "user-1", {"group_name": "우리 가족", "group_profile_image_url": None}
    )

    assert result["invite_code"] == "INVITE01"
    assert result["member_count"] == 1
    assert membership == {
        "user_id": "user-1",
        "group_id": 7,
        "nickname": "환자",
        "relation": "보호자",
    }


def test_join_group_initializes_public_profile(monkeypatch) -> None:
    initialized = []
    monkeypatch.setattr(groups.repository, "ensure_user_profile", initialized.append)
    monkeypatch.setattr(
        groups.repository,
        "get_group_by_invite_code",
        lambda invite_code: {"id": 7, "invite_code": invite_code},
    )
    monkeypatch.setattr(groups.repository, "is_member", lambda group_id, user_id: True)
    monkeypatch.setattr(groups.repository, "count_members", lambda group_id: 1)

    groups.join_group("user-1", "INVITE01")

    assert initialized == ["user-1"]


def test_profile_check_allows_missing_profile(monkeypatch) -> None:
    class Result:
        data = []

    class Query:
        def eq(self, *args):
            return self

        @staticmethod
        def execute():
            return Result()

    class UsersTable:
        @staticmethod
        def select(*args):
            return Query()

        @staticmethod
        def insert(data):
            return Query()

    class AuthAdmin:
        @staticmethod
        def get_user_by_id(user_id):
            user = type(
                "User",
                (),
                {
                    "email": "user@example.com",
                    "user_metadata": {"name": "Tester", "phone_number": "01012345678"},
                },
            )()
            return type("Response", (), {"user": user})()

    class Client:
        auth = type("Auth", (), {"admin": AuthAdmin()})()

        @staticmethod
        def table(name):
            if name == "users":
                return UsersTable()
            return type("InsertTable", (), {"insert": lambda self, data: Query()})()

    monkeypatch.setattr(groups.repository, "_client", lambda: Client())

    groups.repository.ensure_user_profile("user-1")


def test_group_detail_rejects_non_member(monkeypatch) -> None:
    monkeypatch.setattr(groups.repository, "get_group", lambda group_id: {"id": group_id})
    monkeypatch.setattr(groups.repository, "is_member", lambda group_id, user_id: False)

    with pytest.raises(HTTPException) as exc_info:
        groups.get_group_detail("user-1", 7)

    assert exc_info.value.status_code == 403


def test_last_member_cannot_leave(monkeypatch) -> None:
    monkeypatch.setattr(groups.repository, "get_group", lambda group_id: {"id": group_id})
    monkeypatch.setattr(groups.repository, "is_member", lambda group_id, user_id: True)
    monkeypatch.setattr(groups.repository, "count_members", lambda group_id: 1)

    with pytest.raises(HTTPException) as exc_info:
        groups.leave_group("user-1", 7)

    assert exc_info.value.status_code == 409


def test_cheer_rejects_self_and_duplicate(monkeypatch) -> None:
    monkeypatch.setattr(groups.repository, "get_group", lambda group_id: {"id": group_id})
    monkeypatch.setattr(groups.repository, "is_member", lambda group_id, user_id: True)

    with pytest.raises(HTTPException) as self_cheer:
        groups.send_cheer("user-1", 7, "user-1")
    assert self_cheer.value.status_code == 400

    monkeypatch.setattr(groups.repository, "has_cheered_today", lambda *args: True)
    with pytest.raises(HTTPException) as duplicate_cheer:
        groups.send_cheer("user-1", 7, "user-2")
    assert duplicate_cheer.value.status_code == 409
