from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.shared.constants import TRAFFIC_FACTORS


class DistrictInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class DistrictEdgeInput(BaseModel):
    from_district: str
    to_district: str
    distance_km: float = Field(gt=0)


class LocalEdgeInput(BaseModel):
    from_location: str
    to_location: str
    distance_km: float = Field(gt=0)
    parent_district: str


class BusScheduleInput(BaseModel):
    route_id: str
    from_district: str
    to_district: str
    transport_name: str
    departure: time
    arrival: time
    fare: int = Field(ge=0, default=0)


class TrainServiceInput(BaseModel):
    train_no: str
    train_name: str
    from_district: str
    to_district: str
    off_day: str
    departure: time
    arrival: time
    day_offset: int = Field(ge=0, default=0)


class LocationInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    kind: str = Field(min_length=1, max_length=32)
    district_name: str | None = None


class TrainStopInput(BaseModel):
    train_no: str
    train_name: str
    stop_order: int = Field(gt=0)
    station: str
    district_name: str
    arrival: time | None = None
    departure: time | None = None
    day_offset: int = Field(ge=0, default=0)
    cumulative_km: float = Field(ge=0, default=0)


class RoutingConfigInput(BaseModel):
    key: Literal["core_cities", "major_cities", "traffic_factors"]
    value: list[str] | dict[str, float]

    @field_validator("value")
    @classmethod
    def validate_config_value(cls, value, info):
        key = info.data.get("key")
        if key in {"core_cities", "major_cities"}:
            if not isinstance(value, list) or not value or any(not item.strip() for item in value):
                raise ValueError("City configuration must be a non-empty list of names")
            normalized = [item.strip() for item in value]
            if len({item.casefold() for item in normalized}) != len(normalized):
                raise ValueError("City names must be unique")
            return normalized
        if key == "traffic_factors":
            if not isinstance(value, dict) or set(value) != set(TRAFFIC_FACTORS):
                raise ValueError("Traffic configuration must include all six defined time ranges")
            if any(factor <= 0 for factor in value.values()):
                raise ValueError("Traffic factors must be greater than zero")
        return value


class AdminReportReviewRequest(BaseModel):
    status: Literal["VERIFIED", "REJECTED"] | None = None
    admin_response: str | None = None


class AdminReportDetailResponse(BaseModel):
    report_id: str
    user_id: str
    user_name: str | None = None
    user_email: str | None = None
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
    user_deleted: bool = False
    admin_deleted: bool = False

    model_config = ConfigDict(from_attributes=True)


class UserWarningCreateRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)


class UserWarningResponse(BaseModel):
    id: int
    user_id: str
    admin_id: str
    reason: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserBlockRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)


class UserUnblockRequest(BaseModel):
    reason: str | None = None


class UserBlockHistoryResponse(BaseModel):
    id: int
    user_id: str
    admin_id: str
    action: str
    reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserSummaryResponse(BaseModel):
    user_id: str
    full_name: str
    email: str
    role: str
    is_blocked: bool = False
    blocked_reason: str | None = None
    blocked_at: datetime | None = None
    blocked_by: str | None = None
    created_at: datetime
    report_count: int = 0
    warning_count: int = 0

    model_config = ConfigDict(from_attributes=True)

