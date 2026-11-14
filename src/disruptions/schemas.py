from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AffectedSegmentInput(BaseModel):
    transport_mode: Literal["BUS", "TRAIN"]
    affected_segment_id: str = Field(min_length=1, max_length=120)
    segment_description: str = Field(min_length=1, max_length=255)
    from_point: str | None = Field(default=None, max_length=120)
    to_point: str | None = Field(default=None, max_length=120)


class AffectedSegmentResponse(BaseModel):
    id: int
    transport_mode: str
    affected_segment_id: str
    segment_description: str
    from_point: str | None = None
    to_point: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DisruptionAnalyzeRequest(BaseModel):
    description: str = Field(min_length=3, max_length=3000)
    source_name: str | None = Field(default=None, max_length=160)
    source_url: str | None = Field(default=None, max_length=500)
    corrected_location: str | None = Field(default=None, max_length=120)


class ExtractedIncidentInfo(BaseModel):
    is_confident: bool
    location: str | None = None
    transport_mode: str | None = None
    incident_type: str
    cause_code: str
    operational_impact: str
    severity: str
    title: str
    alert_message: str
    matching_confidence: str = "HIGH"
    matching_status: str = "CONFIDENT MATCH"
    clarification_prompt: str | None = None


class AffectedRouteSummary(BaseModel):
    mode: str
    service: str
    origin: str
    destination: str
    matched_section: str


class DisruptionAnalysisPreviewResponse(BaseModel):
    status: Literal["READY", "NEEDS_CLARIFICATION"]
    clarification_message: str | None = None
    extracted: ExtractedIncidentInfo
    affected_segments: list[AffectedSegmentInput] = Field(default_factory=list)
    affected_routes: list[AffectedRouteSummary] = Field(default_factory=list)
    total_affected_routes: int = 0


class SimplifiedDisruptionPublishRequest(BaseModel):
    description: str = Field(min_length=3, max_length=3000)
    source_name: str | None = Field(default=None, max_length=160)
    source_url: str | None = Field(default=None, max_length=500)
    corrected_location: str | None = Field(default=None, max_length=120)


class DisruptionCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    location_name: str = Field(min_length=1, max_length=120)
    transport_mode: Literal["BUS", "TRAIN", "BOTH"]
    cause: str = Field(min_length=2, max_length=60)
    severity: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"] = "MODERATE"
    description: str = Field(min_length=5, max_length=3000)
    alert_message: str = Field(min_length=5, max_length=2000)
    status: Literal["DRAFT", "ACTIVE", "INACTIVE", "RESOLVED", "CANCELLED"] = "DRAFT"
    source_name: str | None = Field(default=None, max_length=160)
    source_url: str | None = Field(default=None, max_length=500)
    source_published_at: datetime | None = None
    admin_notes: str | None = None
    estimated_end_time: datetime | None = None
    affected_segments: list[AffectedSegmentInput] = Field(default_factory=list)


class DisruptionUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    location_name: str | None = Field(default=None, min_length=1, max_length=120)
    transport_mode: Literal["BUS", "TRAIN", "BOTH"] | None = None
    cause: str | None = Field(default=None, min_length=2, max_length=60)
    severity: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"] | None = None
    description: str | None = Field(default=None, min_length=5, max_length=3000)
    alert_message: str | None = Field(default=None, min_length=5, max_length=2000)
    status: Literal["DRAFT", "ACTIVE", "INACTIVE", "RESOLVED", "CANCELLED"] | None = None
    source_name: str | None = Field(default=None, max_length=160)
    source_url: str | None = Field(default=None, max_length=500)
    source_published_at: datetime | None = None
    admin_notes: str | None = None
    estimated_end_time: datetime | None = None
    affected_segments: list[AffectedSegmentInput] | None = None


class DisruptionStatusChangeRequest(BaseModel):
    note: str | None = None


class DisruptionResponse(BaseModel):
    id: int
    disruption_id: str
    title: str
    location_name: str
    transport_mode: str
    cause: str
    severity: str
    description: str
    alert_message: str
    status: str
    source_name: str | None = None
    source_url: str | None = None
    source_published_at: datetime | None = None
    admin_notes: str | None = None
    estimated_end_time: datetime | None = None
    created_by_admin_id: str
    created_at: datetime
    updated_at: datetime
    activated_at: datetime | None = None
    resolved_at: datetime | None = None
    deleted_at: datetime | None = None
    affected_segments: list[AffectedSegmentResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DisruptionAuditLogResponse(BaseModel):
    id: int
    disruption_id: int
    admin_id: str
    action: str
    previous_status: str | None = None
    new_status: str
    change_description: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DisruptionAlertPayload(BaseModel):
    disruption_id: str
    location: str
    transport_mode: str
    cause: str
    severity: str
    status: str
    title: str
    message: str
    affected_segment: str
    estimated_end_time: datetime | None = None
    source_name: str | None = None
    source_url: str | None = None
