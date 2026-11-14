import re
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=5, max_length=160)
    password: str = Field(..., min_length=6, max_length=128)
    confirm_password: str = Field(..., min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError("Invalid email address format")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        password = info.data.get("password")
        if password and v != password:
            raise ValueError("Passwords do not match")
        return v


class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=160)
    password: str


class UserProfileResponse(BaseModel):
    user_id: str
    full_name: str
    email: str
    role: str
    is_blocked: bool = False
    blocked_reason: str | None = None
    blocked_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserAuthResponse(BaseModel):
    user: UserProfileResponse
    access_token: str
    token_type: str = "bearer"


class UserProfileUpdateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=128)
    confirm_password: str = Field(..., min_length=6, max_length=128)

    @field_validator("confirm_password")
    @classmethod
    def new_passwords_match(cls, v: str, info) -> str:
        new_password = info.data.get("new_password")
        if new_password and v != new_password:
            raise ValueError("New passwords do not match")
        return v


class UserPreferencesInput(BaseModel):
    default_transport: Literal["Bus", "Train", "Multimodal", "No Preference"] = "No Preference"
    default_preference: Literal["cheapest", "fastest", "shortest", "balanced"] = "balanced"


class UserPreferencesResponse(BaseModel):
    default_transport: str
    default_preference: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FavouriteRouteInput(BaseModel):
    origin: str = Field(..., min_length=2, max_length=120)
    destination: str = Field(..., min_length=2, max_length=120)

    @field_validator("destination")
    @classmethod
    def distinct_locations(cls, v: str, info) -> str:
        origin = info.data.get("origin")
        if origin and origin.strip().casefold() == v.strip().casefold():
            raise ValueError("Origin and destination must be different")
        return v.strip()


class FavouriteRouteResponse(BaseModel):
    id: int
    user_id: str
    origin: str
    destination: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FavouriteServiceInput(BaseModel):
    transport_type: Literal["bus", "train"]
    service_identifier: str = Field(..., min_length=1, max_length=80)
    service_name: str = Field(..., min_length=1, max_length=160)


class FavouriteServiceResponse(BaseModel):
    id: int
    user_id: str
    transport_type: str
    service_identifier: str
    service_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



class AuditLogResponse(BaseModel):
    id: int
    actor: str
    action: str
    target_type: str
    target_id: str | None
    details: dict | list | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportCreateRequest(BaseModel):
    category: str = Field(..., min_length=2, max_length=80)
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=3000)
    transport_mode: str | None = Field(default="General", max_length=40)
    related_route_info: str | None = Field(default=None, max_length=255)
    evidence_path: str | None = Field(default=None, max_length=255)


class ReportResponse(BaseModel):
    report_id: str
    user_id: str
    category: str
    title: str
    description: str
    transport_mode: str | None = "General"
    related_route_info: str | None = None
    evidence_path: str | None = None
    status: str
    submitted_at: datetime
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    admin_response: str | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseModel):
    id: int
    user_id: str
    report_id: str | None = None
    title: str
    message: str
    notification_type: str = "general"
    is_read: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnreadNotificationCountResponse(BaseModel):
    unread_count: int

