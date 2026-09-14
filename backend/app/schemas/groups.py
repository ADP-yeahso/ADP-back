"""Group, membership, and cheer API contracts."""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class GroupCreate(BaseModel):
    group_name: str = Field(min_length=1, max_length=255)
    group_profile_image_url: str | None = Field(default=None, max_length=500)


class GroupUpdate(BaseModel):
    group_name: str | None = Field(default=None, min_length=1, max_length=255)
    group_profile_image_url: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_update(self) -> "GroupUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class GroupJoin(BaseModel):
    invite_code: str = Field(min_length=1, max_length=100)


class GroupMemberUpdate(BaseModel):
    patients_nickname: str | None = Field(default=None, min_length=1, max_length=255)
    patient_relation: str | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def require_update(self) -> "GroupMemberUpdate":
        if self.patients_nickname is None and self.patient_relation is None:
            raise ValueError("At least one field must be provided")
        return self


class GroupSummary(BaseModel):
    id: int
    group_name: str
    group_profile_image_url: str | None = None
    invite_code: str
    member_count: int
    created_at: datetime


class GroupMember(BaseModel):
    user_id: str
    name: str | None = None
    patients_nickname: str
    patient_relation: str
    joined_at: datetime | None = None


class GroupDetail(GroupSummary):
    members: list[GroupMember]


class CheerCreated(BaseModel):
    id: int
