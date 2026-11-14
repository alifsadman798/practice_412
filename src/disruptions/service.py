import secrets
from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models import (
    DistrictEdge,
    DisruptionAffectedSegment,
    DisruptionAuditLog,
    TrainStop,
    TransportDisruption,
)
from src.disruptions.schemas import (
    DisruptionCreateRequest,
    DisruptionUpdateRequest,
)


def generate_disruption_id() -> str:
    """Generates a random unique alphanumeric disruption identifier."""
    token = secrets.token_hex(4).upper()
    return f"DIS-{token}"


def create_disruption(
    session: Session,
    admin_id: str,
    data: DisruptionCreateRequest,
) -> TransportDisruption:
    dis_id = generate_disruption_id()
    while session.scalar(select(TransportDisruption).where(TransportDisruption.disruption_id == dis_id)):
        dis_id = generate_disruption_id()

    now = datetime.now(timezone.utc)
    act_at = now if data.status == "ACTIVE" else None

    disruption = TransportDisruption(
        disruption_id=dis_id,
        title=data.title.strip(),
        location_name=data.location_name.strip(),
        transport_mode=data.transport_mode,
        cause=data.cause.strip(),
        severity=data.severity,
        description=data.description.strip(),
        alert_message=data.alert_message.strip(),
        source_name=data.source_name.strip() if data.source_name else None,
        source_url=data.source_url.strip() if data.source_url else None,
        source_published_at=data.source_published_at,
        admin_notes=data.admin_notes.strip() if data.admin_notes else None,
        status=data.status,
        estimated_end_time=data.estimated_end_time,
        created_by_admin_id=admin_id,
        activated_at=act_at,
    )
    session.add(disruption)
    session.flush()

    for seg in data.affected_segments:
        segment_row = DisruptionAffectedSegment(
            disruption_id=disruption.id,
            transport_mode=seg.transport_mode,
            affected_segment_id=seg.affected_segment_id.strip(),
            segment_description=seg.segment_description.strip(),
            from_point=seg.from_point.strip() if seg.from_point else None,
            to_point=seg.to_point.strip() if seg.to_point else None,
        )
        session.add(segment_row)

    audit = DisruptionAuditLog(
        disruption_id=disruption.id,
        admin_id=admin_id,
        action="CREATED",
        previous_status=None,
        new_status=disruption.status,
        change_description=f"Created disruption {dis_id}: {disruption.title} (Status: {disruption.status})",
    )
    session.add(audit)
    session.commit()
    session.refresh(disruption)
    return disruption


def update_disruption(
    session: Session,
    admin_id: str,
    disruption: TransportDisruption,
    data: DisruptionUpdateRequest,
) -> TransportDisruption:
    changes = []
    if data.title is not None and data.title.strip() != disruption.title:
        disruption.title = data.title.strip()
        changes.append("title")
    if data.location_name is not None and data.location_name.strip() != disruption.location_name:
        disruption.location_name = data.location_name.strip()
        changes.append("location_name")
    if data.transport_mode is not None and data.transport_mode != disruption.transport_mode:
        disruption.transport_mode = data.transport_mode
        changes.append(f"mode={data.transport_mode}")
    if data.cause is not None and data.cause.strip() != disruption.cause:
        disruption.cause = data.cause.strip()
        changes.append("cause")
    if data.severity is not None and data.severity != disruption.severity:
        disruption.severity = data.severity
        changes.append(f"severity={data.severity}")
    if data.description is not None and data.description.strip() != disruption.description:
        disruption.description = data.description.strip()
        changes.append("description")
    if data.alert_message is not None and data.alert_message.strip() != disruption.alert_message:
        disruption.alert_message = data.alert_message.strip()
        changes.append("alert_message")
    if data.source_name is not None:
        disruption.source_name = data.source_name.strip() if data.source_name else None
    if data.source_url is not None:
        disruption.source_url = data.source_url.strip() if data.source_url else None
    if data.source_published_at is not None:
        disruption.source_published_at = data.source_published_at
    if data.admin_notes is not None:
        disruption.admin_notes = data.admin_notes.strip() if data.admin_notes else None
    if data.estimated_end_time is not None:
        disruption.estimated_end_time = data.estimated_end_time

    if data.status is not None and data.status != disruption.status:
        prev_st = disruption.status
        disruption.status = data.status
        if data.status == "ACTIVE" and not disruption.activated_at:
            disruption.activated_at = datetime.now(timezone.utc)
        if data.status == "RESOLVED":
            disruption.resolved_at = datetime.now(timezone.utc)
        changes.append(f"status {prev_st} -> {data.status}")

    # If new segments provided, replace existing
    if data.affected_segments is not None:
        # Delete old segments
        for old_seg in list(disruption.affected_segments):
            session.delete(old_seg)
        for seg in data.affected_segments:
            new_seg = DisruptionAffectedSegment(
                disruption_id=disruption.id,
                transport_mode=seg.transport_mode,
                affected_segment_id=seg.affected_segment_id.strip(),
                segment_description=seg.segment_description.strip(),
                from_point=seg.from_point.strip() if seg.from_point else None,
                to_point=seg.to_point.strip() if seg.to_point else None,
            )
            session.add(new_seg)
        changes.append("affected_segments")

    audit = DisruptionAuditLog(
        disruption_id=disruption.id,
        admin_id=admin_id,
        action="EDITED",
        previous_status=disruption.status,
        new_status=disruption.status,
        change_description=f"Edited disruption {disruption.disruption_id}: {', '.join(changes) if changes else 'General update'}",
    )
    session.add(audit)
    session.commit()
    session.refresh(disruption)
    return disruption


def change_disruption_status(
    session: Session,
    admin_id: str,
    disruption: TransportDisruption,
    new_status: str,
    note: str | None = None,
) -> TransportDisruption:
    prev_status = disruption.status
    if prev_status == new_status:
        return disruption

    now = datetime.now(timezone.utc)
    disruption.status = new_status
    if new_status == "ACTIVE":
        disruption.activated_at = now
    elif new_status == "RESOLVED":
        disruption.resolved_at = now

    action_name = {
        "ACTIVE": "ACTIVATED",
        "INACTIVE": "DEACTIVATED",
        "RESOLVED": "RESOLVED",
        "CANCELLED": "CANCELLED",
        "DRAFT": "DRAFTED",
    }.get(new_status, f"SET_{new_status}")

    audit = DisruptionAuditLog(
        disruption_id=disruption.id,
        admin_id=admin_id,
        action=action_name,
        previous_status=prev_status,
        new_status=new_status,
        change_description=f"Status changed from {prev_status} to {new_status}. {note or ''}".strip(),
    )
    session.add(audit)
    session.commit()
    session.refresh(disruption)
    return disruption


def soft_delete_disruption(
    session: Session,
    admin_id: str,
    disruption: TransportDisruption,
) -> None:
    disruption.deleted_at = datetime.now(timezone.utc)
    audit = DisruptionAuditLog(
        disruption_id=disruption.id,
        admin_id=admin_id,
        action="DELETED",
        previous_status=disruption.status,
        new_status="ARCHIVED",
        change_description=f"Disruption {disruption.disruption_id} soft deleted / archived by {admin_id}.",
    )
    session.add(audit)
    session.commit()


def get_segment_candidates(session: Session) -> dict:
    """Returns available road edges and railway stations to assist admin in selecting affected segments."""
    edges = session.scalars(select(DistrictEdge).order_by(DistrictEdge.from_district, DistrictEdge.to_district)).all()
    road_candidates = [
        {
            "id": f"edge:{e.from_district}-{e.to_district}",
            "description": f"{e.from_district} ↔ {e.to_district} ({e.distance_km:.1f} km)",
            "from_point": e.from_district,
            "to_point": e.to_district,
            "mode": "BUS",
        }
        for e in edges
    ]

    stops = session.execute(
        select(TrainStop.station, TrainStop.district_name)
        .distinct()
        .order_by(TrainStop.district_name, TrainStop.station)
    ).all()
    rail_candidates = [
        {
            "id": f"station:{st}",
            "description": f"{st} Railway Station ({dist})",
            "from_point": st,
            "to_point": None,
            "mode": "TRAIN",
        }
        for st, dist in stops
    ]

    return {
        "road_segments": road_candidates,
        "rail_stations": rail_candidates,
    }
