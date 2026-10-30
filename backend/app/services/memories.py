"""Memory tree record and interaction use cases."""

from typing import List, Optional

from fastapi import HTTPException, status
from supabase import Client

from app.repositories.memories import (
    create_memory_record,
    delete_memory_record,
    get_memory_record_by_id,
    get_memory_records_by_patient,
    update_memory_record,
)
from app.repositories.patients import check_patient_access
from app.schemas.memories import MemoryRecordCreate, MemoryRecordUpdate
from app.services import media as media_service


def create_memory_service(
    client: Client, patient_id: int, user_id: str, data: MemoryRecordCreate
) -> dict:
    if not check_patient_access(client, patient_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="그룹원 아님: 해당 환자에 접근할 권한이 없습니다."
        )
    return create_memory_record(client, patient_id, user_id, data.model_dump(mode="json"))


def get_memories_service(
    client: Client,
    patient_id: int,
    user_id: str,
    page: int = 1,
    size: int = 20,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> List[dict]:
    if not check_patient_access(client, patient_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="그룹원 아님: 해당 환자에 접근할 권한이 없습니다."
        )
    offset = (page - 1) * size
    records = get_memory_records_by_patient(client, patient_id, size, offset, from_date, to_date)
    media_by_record = media_service.list_memory_records_media([record["id"] for record in records])
    for record in records:
        record["media"] = media_by_record.get(record["id"], [])
        record["bookmarked"] = False
    return records


def get_memory_service(client: Client, record_id: int, user_id: str) -> dict:
    record = get_memory_record_by_id(client, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="기록 없음")
    
    if not check_patient_access(client, record["patient_id"], user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="그룹원 아님")
    
    record["media"] = media_service.list_memory_record_media(record_id, user_id)
    record["bookmarked"] = False
    return record


def update_memory_service(
    client: Client, record_id: int, user_id: str, data: MemoryRecordUpdate
) -> dict:
    record = get_memory_record_by_id(client, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="기록 없음")
    
    # 작성자 본인인지 확인
    if str(record["user_id"]) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="작성자 아님")
    
    update_data = data.model_dump(mode="json", exclude_unset=True)
    if not update_data:
        return record
        
    updated_record = update_memory_record(client, record_id, update_data)
    if not updated_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="업데이트 실패")
        
    updated_record["media"] = media_service.list_memory_record_media(record_id, user_id)
    updated_record["bookmarked"] = False
    return updated_record


def delete_memory_service(client: Client, record_id: int, user_id: str) -> None:
    record = get_memory_record_by_id(client, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="기록 없음")
    
    # 작성자 본인인지 확인
    if str(record["user_id"]) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="작성자 아님")
        
    success = delete_memory_record(client, record_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="삭제 실패")
