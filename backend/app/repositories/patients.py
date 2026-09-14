"""Patient profile and setting persistence."""

from typing import cast

from supabase import Client

def check_patient_access(client: Client, patient_id: int, user_id: str) -> bool:
    """Check if the user is a member of the group the patient belongs to."""
    # 1. Get patient's group_id
    patient_res = client.table("patients").select("group_id").eq("id", patient_id).execute()
    patient_rows = cast(list, patient_res.data)
    if not patient_rows:
        return False
    group_id = patient_rows[0]["group_id"]
    
    # 2. Check if user is in group_members
    member_res = client.table("group_members").select("id").eq("group_id", group_id).eq("user_id", user_id).execute()
    member_rows = cast(list, member_res.data)
    return len(member_rows) > 0
