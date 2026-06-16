"""Device-token API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class DeviceTokenRegisterRequest(BaseModel):
    token: str = Field(..., min_length=8)
    platform: str = Field(..., pattern="^(ios|android|web|macos|windows|unknown)$")


class DeviceTokenResponse(BaseModel):
    id: int
    user_id: int
    token: str
    platform: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
