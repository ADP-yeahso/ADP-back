"""Unit tests for Family Letters (가족 편지함) schemas and validation logic."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.letters import (
    LetterBoxType,
    LetterCreate,
    LetterDetailResponse,
    LetterReadStatusResponse,
    LetterResponse,
)


def test_letter_create_schema_valid():
    """정상적인 편지 생성 요청 스키마 검증."""
    receiver_id = uuid4()
    lc = LetterCreate(
        group_id=1,
        receiver_user_id=receiver_id,
        content="안녕하세요, 할머니 오늘 식사 잘 하셨어요.",
    )
    assert lc.group_id == 1
    assert lc.receiver_user_id == receiver_id
    assert lc.content == "안녕하세요, 할머니 오늘 식사 잘 하셨어요."


def test_letter_create_schema_all_family():
    """'가족 모두에게' 보내는 편지 생성 스키마 (receiver_user_id는 None)."""
    lc = LetterCreate(
        group_id=10,
        receiver_user_id=None,
        content="가족 여러분, 이번 주말에 병원 예약 있습니다.",
    )
    assert lc.group_id == 10
    assert lc.receiver_user_id is None


def test_letter_create_schema_content_max_length_exceeded():
    """500자 초과 편지 본문 작성 시 Pydantic ValidationError (422) 발생 검증."""
    over_500_chars = "가" * 501
    with pytest.raises(ValidationError) as exc_info:
        LetterCreate(
            group_id=1,
            content=over_500_chars,
        )
    errors = exc_info.value.errors()
    assert any(err["type"] == "string_too_long" for err in errors)


def test_letter_box_type_enum():
    """편지함 구분 Enum 검증."""
    assert LetterBoxType.INBOX == "inbox"
    assert LetterBoxType.SENT == "sent"
