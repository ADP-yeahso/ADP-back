"""app/services/letters.py

Service layer for Family Letters (가족 편지함) domain.
Contains core business logic, letter_reads bulk initialization, and manual Python-level
group membership authorization checks to compensate for Supabase Service Role Key bypassing RLS.
"""

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.repositories import letters as repo
from app.schemas.letters import (
    LetterBoxType,
    LetterCreate,
    LetterDetailResponse,
    LetterReadStatusResponse,
    LetterResponse,
)


# ==========================================
# 0. Authorization Verification Helpers
# ==========================================


def validate_group_access(user_id: UUID, group_id: int) -> None:
    """사용자가 해당 그룹의 멤버인지 파이썬 레벨에서 검증한다 (Service Role Key RLS 우회 방지)."""
    if not repo.is_user_in_group(user_id, group_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: User {user_id} is not a member of group {group_id}",
        )


# ==========================================
# 1. Family Letters Service Functions
# ==========================================


def send_letter(sender_user_id: UUID, payload: LetterCreate) -> LetterResponse:
    """가족 편지를 작성 및 전송하고, 수신자(들)에 대한 읽음 상태(letter_reads)를 초기화한다."""
    # 1. 발신자의 그룹 멤버십 검증
    validate_group_access(sender_user_id, payload.group_id)

    # 2. 지정 수신자가 있는 경우, 해당 수신자의 그룹 멤버십 검증
    if payload.receiver_user_id is not None:
        if not repo.is_user_in_group(payload.receiver_user_id, payload.group_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Receiver is not a member of the specified group",
            )

    # 3. 편지 DB 생성 (created_at 생략)
    letter_data: dict[str, Any] = {
        "group_id": payload.group_id,
        "sender_user_id": str(sender_user_id),
        "receiver_user_id": str(payload.receiver_user_id) if payload.receiver_user_id else None,
        "content": payload.content,
    }
    letter = repo.create_letter(letter_data)
    letter_id = letter["id"]

    # 4. 읽음 상태 초기화 로직 (letter_reads)
    reads_payload: list[dict[str, Any]] = []

    if payload.receiver_user_id is not None:
        # 특정 1인 지정 발송: 해당 1명에 대해 레코드 생성
        reads_payload.append({
            "letter_id": letter_id,
            "user_id": str(payload.receiver_user_id),
            "is_read": False,
            "read_at": None,
        })
    else:
        # '가족 모두에게' 발송: 그룹 내 발송자를 제외한 모든 멤버 목록 조회 후 Bulk Insert
        member_user_ids = repo.get_group_member_user_ids(payload.group_id)
        recipient_user_ids = [uid for uid in member_user_ids if uid != sender_user_id]
        
        for recipient_id in recipient_user_ids:
            reads_payload.append({
                "letter_id": letter_id,
                "user_id": str(recipient_id),
                "is_read": False,
                "read_at": None,
            })

    if reads_payload:
        repo.create_letter_reads(reads_payload)

    return LetterResponse(
        id=letter["id"],
        group_id=letter["group_id"],
        sender_user_id=UUID(letter["sender_user_id"]),
        receiver_user_id=UUID(letter["receiver_user_id"]) if letter.get("receiver_user_id") else None,
        content=letter["content"],
        created_at=letter["created_at"],
        is_read=None,
        read_at=None,
    )


def get_letter_detail(user_id: UUID, letter_id: int) -> LetterDetailResponse:
    """편지 단건 상세 정보를 조회하고, 읽지 않은 수신자인 경우 읽음 처리를 수행한다."""
    # 1. 편지 존재 및 Soft Delete 여부 확인
    letter = repo.get_letter_by_id(letter_id)
    if not letter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Letter with id {letter_id} not found",
        )

    # 2. 그룹 멤버십 검증
    validate_group_access(user_id, letter["group_id"])

    sender_id = UUID(letter["sender_user_id"])
    receiver_id = UUID(letter["receiver_user_id"]) if letter.get("receiver_user_id") else None

    # 3. 본인이 수신자(특정 지정 또는 전체 발송)이고 발신자가 아닌 경우 자동 읽음 처리
    is_recipient = (receiver_id is None or receiver_id == user_id) and (sender_id != user_id)
    if is_recipient:
        current_read = repo.get_letter_read_status(letter_id, user_id)
        if current_read and not current_read.get("is_read"):
            repo.mark_letter_as_read(letter_id, user_id)

    # 4. 전체 수신자 읽음 상태 목록 및 현재 요청자의 읽음 상태 가져오기
    reads_data = repo.list_letter_reads(letter_id)
    user_read = repo.get_letter_read_status(letter_id, user_id)

    reads_responses = [
        LetterReadStatusResponse(
            user_id=UUID(r["user_id"]),
            is_read=r["is_read"],
            read_at=r.get("read_at"),
        )
        for r in reads_data
    ]

    return LetterDetailResponse(
        id=letter["id"],
        group_id=letter["group_id"],
        sender_user_id=sender_id,
        receiver_user_id=receiver_id,
        content=letter["content"],
        created_at=letter["created_at"],
        is_read=user_read["is_read"] if user_read else None,
        read_at=user_read.get("read_at") if user_read else None,
        reads=reads_responses,
    )


def list_letters(
    user_id: UUID,
    group_id: int,
    box_type: LetterBoxType = LetterBoxType.INBOX,
) -> list[LetterResponse]:
    """그룹 단위 수신함(inbox) 또는 발신함(sent) 편지 목록을 조회한다."""
    # 1. 그룹 멤버십 검증
    validate_group_access(user_id, group_id)

    # 2. 편지 목록 DB 조회
    raw_letters = repo.list_letters_by_group(group_id, user_id, box_type.value)

    # 3. 각 편지별 요청자 시점의 읽음 상태 매핑
    result: list[LetterResponse] = []
    for letter in raw_letters:
        user_read = repo.get_letter_read_status(letter["id"], user_id)
        result.append(
            LetterResponse(
                id=letter["id"],
                group_id=letter["group_id"],
                sender_user_id=UUID(letter["sender_user_id"]),
                receiver_user_id=UUID(letter["receiver_user_id"]) if letter.get("receiver_user_id") else None,
                content=letter["content"],
                created_at=letter["created_at"],
                is_read=user_read["is_read"] if user_read else None,
                read_at=user_read.get("read_at") if user_read else None,
            )
        )
    return result


def delete_letter(user_id: UUID, letter_id: int) -> None:
    """편지를 Soft Delete 처리한다 (작성자 본인만 삭제 가능)."""
    # 1. 편지 존재 확인
    letter = repo.get_letter_by_id(letter_id)
    if not letter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Letter with id {letter_id} not found",
        )

    # 2. 그룹 멤버십 검증
    validate_group_access(user_id, letter["group_id"])

    # 3. 작성자 본인 확인
    if str(letter["sender_user_id"]) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only the letter author can delete this letter",
        )

    # 4. Soft Delete 수행
    repo.soft_delete_letter(letter_id)


def get_letter_reads(user_id: UUID, letter_id: int) -> list[LetterReadStatusResponse]:
    """특정 편지의 수신자별 읽음 현황 목록을 조회한다."""
    # 1. 편지 존재 확인
    letter = repo.get_letter_by_id(letter_id)
    if not letter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Letter with id {letter_id} not found",
        )

    # 2. 그룹 멤버십 검증
    validate_group_access(user_id, letter["group_id"])

    # 3. 읽음 현황 목록 조회 및 변환
    reads_data = repo.list_letter_reads(letter_id)
    return [
        LetterReadStatusResponse(
            user_id=UUID(r["user_id"]),
            is_read=r["is_read"],
            read_at=r.get("read_at"),
        )
        for r in reads_data
    ]
