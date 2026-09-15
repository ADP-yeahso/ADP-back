"""Patient request and response schemas."""

from datetime import date

from pydantic import BaseModel, Field, model_validator


class PatientCreate(BaseModel):
    patient_name: str = Field(min_length=1, max_length=255)
    patient_birth_date: date
    gender: str = Field(min_length=1, max_length=30)
    profile_image_url: str | None = Field(default=None, max_length=500)
    memo: str | None = Field(default=None, max_length=1000)
    diagnosis_date: date | None = None
    primary_hospital: str | None = Field(default=None, max_length=255)


class PatientUpdate(BaseModel):
    patient_name: str | None = Field(default=None, min_length=1, max_length=255)
    patient_birth_date: date | None = None
    gender: str | None = Field(default=None, min_length=1, max_length=30)
    profile_image_url: str | None = Field(default=None, max_length=500)
    memo: str | None = Field(default=None, max_length=1000)
    diagnosis_date: date | None = None
    primary_hospital: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def require_update(self) -> "PatientUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class PatientResponse(BaseModel):
    id: int
    patient_name: str
    patient_birth_date: date
    gender: str
    profile_image_url: str | None = None
    memo: str | None = None
    diagnosis_date: date | None = None
    primary_hospital: str | None = None
