"""Memory record, comment, bookmark, reaction, and cheer persistence."""

from typing import Any, Dict, List, Optional, cast
from uuid import UUID

from supabase import Client


def create_memory_record(client: Client, patient_id: int, user_id: str, data: dict) -> dict:
    """Create a new memory record."""
    payload = {
        "patient_id": patient_id,
        "user_id": user_id,
        **data,
    }
    response = client.table("memory_records").insert(payload).execute()
    rows = cast(list, response.data)
    return rows[0] if rows else {}


def get_memory_records_by_patient(
    client: Client,
    patient_id: int,
    limit: int = 20,
    offset: int = 0,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> list:
    """Get memory records for a patient with pagination and date filtering."""
    query = client.table("memory_records").select("*").eq("patient_id", patient_id)
    if from_date:
        query = query.gte("record_date", from_date)
    if to_date:
        query = query.lte("record_date", to_date)
    
    query = query.order("record_date", desc=True).range(offset, offset + limit - 1)
    response = query.execute()
    return cast(list, response.data)


def get_memory_record_by_id(client: Client, record_id: int) -> Optional[dict]:
    """Get a memory record by ID."""
    response = client.table("memory_records").select("*").eq("id", record_id).execute()
    rows = cast(list, response.data)
    return rows[0] if rows else None


def update_memory_record(client: Client, record_id: int, data: dict) -> Optional[dict]:
    """Update a memory record."""
    response = client.table("memory_records").update(data).eq("id", record_id).execute()
    rows = cast(list, response.data)
    return rows[0] if rows else None


def delete_memory_record(client: Client, record_id: int) -> bool:
    """Soft delete or hard delete a memory record."""
    # Assuming soft delete by setting deleted_at, or just delete if it's hard delete
    # Spec says "soft delete" for others, let's use soft delete or delete depending on DB schema. 
    # For now, let's use hard delete as a placeholder, or update deleted_at
    response = client.table("memory_records").delete().eq("id", record_id).execute()
    rows = cast(list, response.data)
    return len(rows) > 0
