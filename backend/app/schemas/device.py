"""Device-token API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class DeviceTokenRegisterRequest(BaseModel):
    token: str = Field(..., min_length=8)
    platform: str = Field(..., pattern="^(web|android|ios|expo|macos|windows|unknown)$")
    device_name: str | None = Field(default=None, max_length=120)
    browser: str | None = Field(default=None, max_length=80)


class DeviceTokenResponse(BaseModel):
    id: int
    user_id: int
    token: str
    platform: str
    device_name: str | None = None
    browser: str | None = None
    is_active: bool = True
    last_seen_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
