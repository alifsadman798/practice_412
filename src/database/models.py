from datetime import datetime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class District(Base):
    __tablename__ = "districts"

    name: Mapped[str] = mapped_column(String(120), primary_key=True)


class Location(Base):
    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String(160), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    district_name: Mapped[str | None] = mapped_column(
        ForeignKey("districts.name", ondelete="SET NULL")
    )


class DistrictEdge(Base):
    __tablename__ = "district_edges"
    __table_args__ = (
        UniqueConstraint("from_district", "to_district", name="uq_district_edge"),
        CheckConstraint("distance_km > 0", name="ck_district_distance_positive"),
        CheckConstraint("from_district < to_district", name="ck_district_edge_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_district: Mapped[str] = mapped_column(
        ForeignKey("districts.name", ondelete="CASCADE"), nullable=False
    )
    to_district: Mapped[str] = mapped_column(
        ForeignKey("districts.name", ondelete="CASCADE"), nullable=False
    )
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)


class LocalEdge(Base):
    __tablename__ = "local_edges"
    __table_args__ = (
        UniqueConstraint("from_location", "to_location", name="uq_local_edge"),
        CheckConstraint("distance_km > 0", name="ck_local_distance_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_location: Mapped[str] = mapped_column(
        ForeignKey("locations.name", ondelete="CASCADE"), nullable=False
    )
    to_location: Mapped[str] = mapped_column(
        ForeignKey("locations.name", ondelete="CASCADE"), nullable=False
    )
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    parent_district: Mapped[str] = mapped_column(
        ForeignKey("districts.name", ondelete="CASCADE"), nullable=False
    )


class BusSchedule(Base):
    __tablename__ = "bus_schedules"
    __table_args__ = (
        UniqueConstraint(
            "route_id",
            "from_district",
            "to_district",
            "transport_name",
            "departure",
            "arrival",
            name="uq_bus_schedule",
        ),
        Index("ix_bus_lookup", "from_district", "to_district", "departure"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[str] = mapped_column(String(40), nullable=False)
    from_district: Mapped[str] = mapped_column(
        ForeignKey("districts.name", ondelete="CASCADE"), nullable=False
    )
    to_district: Mapped[str] = mapped_column(
        ForeignKey("districts.name", ondelete="CASCADE"), nullable=False
    )
    transport_name: Mapped[str] = mapped_column(String(160), nullable=False)
    departure: Mapped[object] = mapped_column(Time, nullable=False)
    arrival: Mapped[object] = mapped_column(Time, nullable=False)
    fare: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class TrainService(Base):
    __tablename__ = "train_services"
    __table_args__ = (
        UniqueConstraint("train_no", name="uq_train_number"),
        UniqueConstraint("train_no", "from_district", name="uq_train_direction"),
        Index("ix_train_no", "train_no"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    train_no: Mapped[str] = mapped_column(String(32), nullable=False)
    train_name: Mapped[str] = mapped_column(String(160), nullable=False)
    from_district: Mapped[str] = mapped_column(
        ForeignKey("districts.name", ondelete="CASCADE"), nullable=False
    )
    to_district: Mapped[str] = mapped_column(
        ForeignKey("districts.name", ondelete="CASCADE"), nullable=False
    )
    off_day: Mapped[str] = mapped_column(String(20), nullable=False)
    departure: Mapped[object] = mapped_column(Time, nullable=False)
    arrival: Mapped[object] = mapped_column(Time, nullable=False)
    day_offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class TrainStop(Base):
    __tablename__ = "train_stops"
    __table_args__ = (
        UniqueConstraint("train_no", "stop_order", name="uq_train_stop_order"),
        CheckConstraint("stop_order > 0", name="ck_train_stop_order_positive"),
        Index("ix_train_stop_station", "district_name", "train_no"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    train_no: Mapped[str] = mapped_column(
        ForeignKey("train_services.train_no", ondelete="CASCADE"), nullable=False
    )
    train_name: Mapped[str] = mapped_column(String(160), nullable=False)
    stop_order: Mapped[int] = mapped_column(Integer, nullable=False)
    station: Mapped[str] = mapped_column(String(160), nullable=False)
    district_name: Mapped[str] = mapped_column(
        ForeignKey("districts.name", ondelete="CASCADE"), nullable=False
    )
    arrival: Mapped[object | None] = mapped_column(Time)
    departure: Mapped[object | None] = mapped_column(Time)
    day_offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cumulative_km: Mapped[float] = mapped_column(Float, nullable=False, default=0)


class RoutingConfig(Base):
    __tablename__ = "routing_config"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict | list] = mapped_column(JSON, nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False
    )
    default_transport: Mapped[str] = mapped_column(String(40), default="No Preference", nullable=False)
    default_preference: Mapped[str] = mapped_column(String(40), default="balanced", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class FavouriteRoute(Base):
    __tablename__ = "favourite_routes"
    __table_args__ = (
        UniqueConstraint("user_id", "origin", "destination", name="uq_user_fav_route"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    origin: Mapped[str] = mapped_column(String(120), nullable=False)
    destination: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FavouriteService(Base):
    __tablename__ = "favourite_services"
    __table_args__ = (
        UniqueConstraint("user_id", "transport_type", "service_identifier", name="uq_user_fav_service"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    transport_type: Mapped[str] = mapped_column(String(20), nullable=False)
    service_identifier: Mapped[str] = mapped_column(String(80), nullable=False)
    service_name: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(60), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserReport(Base):
    __tablename__ = "user_reports"
    __table_args__ = (
        Index("ix_reports_user", "user_id"),
        Index("ix_reports_status", "status"),
        Index("ix_reports_submitted", "submitted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    transport_mode: Mapped[str | None] = mapped_column(String(40), default="General", nullable=True)
    related_route_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    admin_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notif_user_read", "user_id", "is_read"),
        Index("ix_notif_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    report_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(40), default="general", nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserWarning(Base):
    __tablename__ = "user_warnings"
    __table_args__ = (
        Index("ix_warnings_user", "user_id"),
        Index("ix_warnings_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    admin_id: Mapped[str] = mapped_column(String(80), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserBlockHistory(Base):
    __tablename__ = "user_block_history"
    __table_args__ = (
        Index("ix_block_history_user", "user_id"),
        Index("ix_block_history_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    admin_id: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # BLOCK, UNBLOCK
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TransportDisruption(Base):
    __tablename__ = "transport_disruptions"
    __table_args__ = (
        Index("ix_disruptions_status", "status"),
        Index("ix_disruptions_location", "location_name"),
        Index("ix_disruptions_mode", "transport_mode"),
        Index("ix_disruptions_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    disruption_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    location_name: Mapped[str] = mapped_column(String(120), nullable=False)
    transport_mode: Mapped[str] = mapped_column(String(20), nullable=False)  # BUS, TRAIN, BOTH
    cause: Mapped[str] = mapped_column(String(60), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="MODERATE")  # LOW, MODERATE, HIGH, CRITICAL
    description: Mapped[str] = mapped_column(Text, nullable=False)
    alert_message: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False)  # DRAFT, ACTIVE, INACTIVE, RESOLVED, CANCELLED
    estimated_end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_admin_id: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    affected_segments: Mapped[list["DisruptionAffectedSegment"]] = relationship(
        "DisruptionAffectedSegment", back_populates="disruption", cascade="all, delete-orphan", lazy="selectin"
    )


class DisruptionAffectedSegment(Base):
    __tablename__ = "disruption_affected_segments"
    __table_args__ = (
        Index("ix_affected_disruption", "disruption_id"),
        Index("ix_affected_mode_seg", "transport_mode", "affected_segment_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    disruption_id: Mapped[int] = mapped_column(
        ForeignKey("transport_disruptions.id", ondelete="CASCADE"), nullable=False
    )
    transport_mode: Mapped[str] = mapped_column(String(20), nullable=False)  # BUS, TRAIN
    affected_segment_id: Mapped[str] = mapped_column(String(120), nullable=False)
    segment_description: Mapped[str] = mapped_column(String(255), nullable=False)
    from_point: Mapped[str | None] = mapped_column(String(120), nullable=True)
    to_point: Mapped[str | None] = mapped_column(String(120), nullable=True)

    disruption: Mapped["TransportDisruption"] = relationship("TransportDisruption", back_populates="affected_segments")


class DisruptionAuditLog(Base):
    __tablename__ = "disruption_audit_logs"
    __table_args__ = (
        Index("ix_disruption_audit_disruption", "disruption_id"),
        Index("ix_disruption_audit_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    disruption_id: Mapped[int] = mapped_column(Integer, nullable=False)
    admin_id: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    change_description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
