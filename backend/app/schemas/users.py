from pydantic import BaseModel, ConfigDict, Field


class UserProfileUpsert(BaseModel):
	name: str = Field(min_length=1, max_length=255)
	phone_number: str = Field(min_length=1, max_length=30)
	profile_image_url: str | None = Field(default=None, max_length=500)


class UserProfileResponse(UserProfileUpsert):
	model_config = ConfigDict(from_attributes=True)

	id: str
	email: str
