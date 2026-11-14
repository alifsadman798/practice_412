from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.auth.security import require_admin
from src.database.connection import get_db
from src.database.models import DisruptionAuditLog, TransportDisruption
from src.disruptions import service
from src.disruptions.extractor import extract_incident_details
from src.disruptions.route_detector import detect_affected_segments_and_routes
from src.disruptions.schemas import (
    DisruptionAnalysisPreviewResponse,
    DisruptionAnalyzeRequest,
    DisruptionAuditLogResponse,
    DisruptionCreateRequest,
    DisruptionResponse,
    DisruptionStatusChangeRequest,
    DisruptionUpdateRequest,
    ExtractedIncidentInfo,
    SimplifiedDisruptionPublishRequest,
)

router = APIRouter(prefix="/api/admin/disruptions", tags=["Admin Transport Disruptions"])


def _get_disruption_or_404(session: Session, disruption_id: str) -> TransportDisruption:
    stmt = select(TransportDisruption).where(
        or_(
            TransportDisruption.disruption_id == disruption_id.strip(),
            (
                TransportDisruption.id == int(disruption_id)
                if disruption_id.strip().isdigit()
                else False
            ),
        )
    )
    disruption = session.scalar(stmt)
    if not disruption:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disruption alert '{disruption_id}' not found.",
        )
    return disruption


@router.post("/analyze", response_model=DisruptionAnalysisPreviewResponse)
def admin_analyze_disruption(
    body: DisruptionAnalyzeRequest,
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    """
    Analyzes natural language incident description, extracts incident parameters,
    identifies affected network sections, and automatically detects affected routes.
    """
    incident = extract_incident_details(body.description, body.corrected_location)
    if not incident.is_confident:
        return DisruptionAnalysisPreviewResponse(
            status="NEEDS_CLARIFICATION",
            clarification_message=incident.clarification_prompt,
            extracted=ExtractedIncidentInfo(
                is_confident=False,
                location=incident.location,
                transport_mode=incident.transport_mode,
                incident_type=incident.incident_type,
                cause_code=incident.cause_code,
                operational_impact=incident.operational_impact,
                severity=incident.severity,
                title=incident.title,
                alert_message=incident.alert_message,
                matching_confidence=incident.matching_confidence,
                matching_status=incident.matching_status,
                clarification_prompt=incident.clarification_prompt,
            ),
            affected_segments=[],
            affected_routes=[],
            total_affected_routes=0,
        )

    segments, routes = detect_affected_segments_and_routes(session, incident)

    return DisruptionAnalysisPreviewResponse(
        status="READY",
        clarification_message=None,
        extracted=ExtractedIncidentInfo(
            is_confident=True,
            location=incident.location,
            transport_mode=incident.transport_mode,
            incident_type=incident.incident_type,
            cause_code=incident.cause_code,
            operational_impact=incident.operational_impact,
            severity=incident.severity,
            title=incident.title,
            alert_message=incident.alert_message,
            matching_confidence=incident.matching_confidence,
            matching_status=incident.matching_status,
            clarification_prompt=None,
        ),
        affected_segments=segments,
        affected_routes=routes,
        total_affected_routes=len(routes),
    )


@router.post("/publish-simplified", response_model=DisruptionResponse, status_code=status.HTTP_201_CREATED)
def admin_publish_simplified_disruption(
    body: SimplifiedDisruptionPublishRequest,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    """
    One-click simplified publication: extracts incident parameters, automatically detects affected network
    segments and routes, and publishes an active transport disruption alert.
    """
    incident = extract_incident_details(body.description, body.corrected_location)
    if not incident.is_confident:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish alert: {incident.clarification_prompt}",
        )

    segments, _ = detect_affected_segments_and_routes(session, incident)

    create_payload = DisruptionCreateRequest(
        title=incident.title,
        location_name=incident.location,
        transport_mode=incident.transport_mode,
        cause=incident.incident_type,
        severity=incident.severity,
        description=body.description.strip(),
        alert_message=incident.alert_message,
        status="ACTIVE",
        source_name=body.source_name,
        source_url=body.source_url,
        affected_segments=segments,
    )
    disruption = service.create_disruption(session, admin_user, create_payload)
    return disruption


@router.post("", response_model=DisruptionResponse, status_code=status.HTTP_201_CREATED)
def admin_create_disruption(
    body: DisruptionCreateRequest,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    """Creates a new transport disruption alert with specified affected road/railway segments."""
    disruption = service.create_disruption(session, admin_user, body)
    return disruption


@router.get("", response_model=list[DisruptionResponse])
def admin_list_disruptions(
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    status: str | None = None,
    transport_mode: str | None = None,
    location: str | None = None,
    search: str | None = None,
    include_deleted: bool = False,
):
    """Lists transport disruptions with optional status, transport mode, and location filtering."""
    stmt = select(TransportDisruption)
    if not include_deleted:
        stmt = stmt.where(TransportDisruption.deleted_at == None)

    if status and status.lower() != "all":
        stmt = stmt.where(func.upper(TransportDisruption.status) == status.strip().upper())

    if transport_mode and transport_mode.lower() != "all":
        stmt = stmt.where(func.upper(TransportDisruption.transport_mode) == transport_mode.strip().upper())

    if location and location.strip():
        loc_term = f"%{location.strip().lower()}%"
        stmt = stmt.where(func.lower(TransportDisruption.location_name).like(loc_term))

    if search and search.strip():
        search_term = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(TransportDisruption.disruption_id).like(search_term),
                func.lower(TransportDisruption.title).like(search_term),
                func.lower(TransportDisruption.location_name).like(search_term),
                func.lower(TransportDisruption.alert_message).like(search_term),
                func.lower(TransportDisruption.cause).like(search_term),
            )
        )

    stmt = stmt.order_by(TransportDisruption.created_at.desc())
    disruptions = session.scalars(stmt).all()
    return disruptions


@router.get("/segments/candidates")
def admin_get_segment_candidates(
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    """Returns available road network edges and railway stations for populating segment pickers."""
    return service.get_segment_candidates(session)


@router.get("/{disruption_id}", response_model=DisruptionResponse)
def admin_get_disruption(
    disruption_id: str,
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    """Retrieves full details of a specific transport disruption including affected segments."""
    disruption = _get_disruption_or_404(session, disruption_id)
    return disruption


@router.put("/{disruption_id}", response_model=DisruptionResponse)
def admin_update_disruption(
    disruption_id: str,
    body: DisruptionUpdateRequest,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    """Updates an existing disruption record and regenerates affected segments if provided."""
    disruption = _get_disruption_or_404(session, disruption_id)
    updated = service.update_disruption(session, admin_user, disruption, body)
    return updated


@router.post("/{disruption_id}/activate", response_model=DisruptionResponse)
@router.post("/{disruption_id}/active", response_model=DisruptionResponse)
def admin_activate_disruption(
    disruption_id: str,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    body: DisruptionStatusChangeRequest | None = None,
):
    """Activates a transport disruption so it immediately attaches alerts to matching route searches."""
    disruption = _get_disruption_or_404(session, disruption_id)
    note = body.note if body else None
    return service.change_disruption_status(session, admin_user, disruption, "ACTIVE", note)


@router.post("/{disruption_id}/deactivate", response_model=DisruptionResponse)
@router.post("/{disruption_id}/inactive", response_model=DisruptionResponse)
def admin_deactivate_disruption(
    disruption_id: str,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    body: DisruptionStatusChangeRequest | None = None,
):
    """Deactivates a disruption so it no longer alerts users on future route searches."""
    disruption = _get_disruption_or_404(session, disruption_id)
    note = body.note if body else None
    return service.change_disruption_status(session, admin_user, disruption, "INACTIVE", note)


@router.post("/{disruption_id}/resolve", response_model=DisruptionResponse)
@router.post("/{disruption_id}/resolved", response_model=DisruptionResponse)
def admin_resolve_disruption(
    disruption_id: str,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    body: DisruptionStatusChangeRequest | None = None,
):
    """Marks a transport disruption as RESOLVED, recording resolution timestamp and audit trail."""
    disruption = _get_disruption_or_404(session, disruption_id)
    note = body.note if body else None
    return service.change_disruption_status(session, admin_user, disruption, "RESOLVED", note)


@router.post("/{disruption_id}/cancel", response_model=DisruptionResponse)
@router.post("/{disruption_id}/cancelled", response_model=DisruptionResponse)
def admin_cancel_disruption(
    disruption_id: str,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    body: DisruptionStatusChangeRequest | None = None,
):
    """Marks a disruption as CANCELLED (e.g., false alarm or cancelled incident)."""
    disruption = _get_disruption_or_404(session, disruption_id)
    note = body.note if body else None
    return service.change_disruption_status(session, admin_user, disruption, "CANCELLED", note)


@router.delete("/{disruption_id}")
def admin_delete_disruption(
    disruption_id: str,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    """Soft deletes a transport disruption, retaining audit history for compliance and review."""
    disruption = _get_disruption_or_404(session, disruption_id)
    service.soft_delete_disruption(session, admin_user, disruption)
    return {"message": f"Transport disruption '{disruption.disruption_id}' successfully soft deleted."}


@router.get("/{disruption_id}/audit-logs", response_model=list[DisruptionAuditLogResponse])
def admin_get_disruption_audit_logs(
    disruption_id: str,
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    """Returns the full chronological audit history of changes made to this disruption alert."""
    disruption = _get_disruption_or_404(session, disruption_id)
    logs = session.scalars(
        select(DisruptionAuditLog)
        .where(DisruptionAuditLog.disruption_id == disruption.id)
        .order_by(DisruptionAuditLog.created_at.asc())
    ).all()
    return logs
