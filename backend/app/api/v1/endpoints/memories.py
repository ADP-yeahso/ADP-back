"""Memory record and interaction endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from supabase import Client

from app.core.security import AuthenticatedUser, get_current_user
from app.db.supabase import get_supabase_client
from app.schemas.memories import (
    MemoryRecordCreate,
    MemoryRecordResponse,
    MemoryRecordUpdate,
)
from app.schemas.media import Media, MediaUploadResponse
from app.services import media as media_service
from app.services.memories import (
    create_memory_service,
    delete_memory_service,
    get_memories_service,
    get_memory_service,
    update_memory_service,
)

router = APIRouter()


@router.post(
    "/patients/{patient_id}/memory-records",
    response_model=MemoryRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="기억 기록 생성",
)
def create_memory_record(
    patient_id: int,
    data: MemoryRecordCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    client: Client = Depends(get_supabase_client),
):
    return create_memory_service(client, patient_id, str(current_user.id), data)


@router.get(
    "/patients/{patient_id}/memory-records",
    response_model=List[MemoryRecordResponse],
    summary="기억 기록 목록 조회",
)
def get_memory_records(
    patient_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
    client: Client = Depends(get_supabase_client),
):
    return get_memories_service(
        client, patient_id, str(current_user.id), page, size, from_date, to_date
    )


@router.get(
    "/memory-records/{record_id}",
    response_model=MemoryRecordResponse,
    summary="기억 기록 상세 조회",
)
def get_memory_record(
    record_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    client: Client = Depends(get_supabase_client),
):
    return get_memory_service(client, record_id, str(current_user.id))


@router.patch(
    "/memory-records/{record_id}",
    response_model=MemoryRecordResponse,
    summary="기억 기록 수정",
)
def update_memory_record(
    record_id: int,
    data: MemoryRecordUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    client: Client = Depends(get_supabase_client),
):
    return update_memory_service(client, record_id, str(current_user.id), data)


@router.delete(
    "/memory-records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="기억 기록 삭제",
)
def delete_memory_record(
    record_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    client: Client = Depends(get_supabase_client),
):
    delete_memory_service(client, record_id, str(current_user.id))


@router.post(
    "/memory-records/{record_id}/media",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="기억 기록 미디어 첨부",
)
async def upload_memory_record_media(
    record_id: int,
    file: UploadFile = File(...),
    duration: int | None = Form(default=None, ge=0),
    sort_order: int = Form(default=0, ge=0, le=32767),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    content = await file.read(media_service.MAX_FILE_SIZE + 1)
    return media_service.upload_memory_record_media(
        record_id, str(current_user.id), file.filename, file.content_type,
        content, duration, sort_order,
    )


@router.get(
    "/memory-records/{record_id}/media",
    response_model=list[Media],
    summary="기억 기록 미디어 목록",
)
def list_memory_record_media(
    record_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return media_service.list_memory_record_media(record_id, str(current_user.id))


@router.delete(
    "/memory-records/{record_id}/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="기억 기록 미디어 삭제",
)
def delete_memory_record_media(
    record_id: int,
    media_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    media_service.delete_memory_record_media(record_id, media_id, str(current_user.id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
