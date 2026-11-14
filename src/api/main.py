import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, Security, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from src.auth.security import decode_access_token

from src.database.connection import engine, get_db
from src.database.base import Base
from src.database.models import (
    AuditLog,
    BusSchedule,
    District,
    DistrictEdge,
    LocalEdge,
    Location,
    Notification,
    RoutingConfig,
    TrainService,
    TrainStop,
    User,
    UserBlockHistory,
    UserReport,
    UserWarning,
)
from src.data.normalize import normalize_name
from src.train.router import train_timetable
from src.api import user_routes
from src.disruptions.admin_routes import router as disruptions_admin_router
from src.api.user_schemas import UserProfileResponse
from src.api.admin_schemas import (
    AdminReportDetailResponse,
    AdminReportReviewRequest,
    AdminUserSummaryResponse,
    BusScheduleInput,
    RoutingConfigInput,
    TrainServiceInput,
    TrainStopInput,
    UserBlockHistoryResponse,
    UserBlockRequest,
    UserUnblockRequest,
    UserWarningCreateRequest,
    UserWarningResponse,
)
from src.api.orchestrator import search_routes
from src.shared.constants import APP_VERSION, BANGLADESH_64_DISTRICTS
from src.shared.models import (
    BusTimetableItem,
    LocalTransportItem,
    RouteSearchRequest,
    RouteSearchResponse,
    TrainTimetableItem,
)
from src.api.user_schemas import AuditLogResponse

security = HTTPBasic(auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)
app_dir = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        logger.warning("Could not auto-create tables on startup: %s", exc)
    yield


app = FastAPI(
    title="SmartRoute BD",
    description="Database-backed multimodal transport route planner for Bangladesh.",
    version=APP_VERSION,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=app_dir / "static"), name="static")
if (app_dir / "image").exists():
    app.mount("/image", StaticFiles(directory=app_dir / "image"), name="image")

app.include_router(user_routes.router)
app.include_router(disruptions_admin_router)


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_: Request, exc: SQLAlchemyError):
    logger.error(
        "Database operation failed",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=503,
        content={"detail": "Database unavailable; transport data could not be queried."},
    )


def require_admin(
    credentials: Annotated[HTTPBasicCredentials | None, Security(security)] = None,
    bearer: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)] = None,
) -> str:
    # 1. Bearer JWT Token (Admin logged in on user interface or persisted in browser)
    if bearer and bearer.credentials:
        payload = decode_access_token(bearer.credentials)
        if payload and (payload.get("role") == "admin" or payload.get("sub") == "SRU-ADMIN"):
            return payload.get("email", "admin")

    # 2. HTTP Basic Auth
    if credentials:
        username = os.getenv("ADMIN_USERNAME", "admin")
        password = os.getenv("ADMIN_PASSWORD", "12345678")
        if secrets.compare_digest(credentials.username, username) and secrets.compare_digest(credentials.password, password):
            return credentials.username

    raise HTTPException(
        status_code=401,
        detail="Invalid admin credentials. Please log in as administrator.",
        headers={"WWW-Authenticate": "Basic"},
    )


def log_admin_action(
    session: Session,
    actor: str,
    action: str,
    target_type: str,
    target_id: str | None = None,
    details: dict | None = None,
):
    log = AuditLog(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        details=details,
    )
    session.add(log)


def commit_or_conflict(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="The record conflicts with existing transport data"
        ) from exc


@app.get("/", include_in_schema=False)
@app.get("/journey", include_in_schema=False)
@app.get("/plan", include_in_schema=False)
@app.get("/timetables", include_in_schema=False)
def home():
    return FileResponse(app_dir / "static" / "index.html")


@app.get("/admin", include_in_schema=False)
def admin_page():
    return FileResponse(app_dir / "static" / "admin.html")


@app.get("/api/health", tags=["System"])
def health(session: Annotated[Session, Depends(get_db)]):
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.error(
            "Database health check failed",
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "database": "unavailable"},
        )
    return {"status": "ok", "database": "ok"}


@app.get("/api/version", tags=["System"])
def version():
    return {"name": "SmartRoute BD", "version": APP_VERSION}


@app.get("/api/districts", response_model=list[str], tags=["Locations"])
def districts(session: Annotated[Session, Depends(get_db)]):
    return BANGLADESH_64_DISTRICTS


@app.get("/api/locations", tags=["Locations"])
def locations(session: Annotated[Session, Depends(get_db)]):
    return [
        {
            "name": row.name,
            "kind": row.kind,
            "district_name": row.district_name,
        }
        for row in session.scalars(select(Location).order_by(Location.name))
    ]


@app.post("/api/search", response_model=RouteSearchResponse, tags=["Routing"])
def search(
    request: RouteSearchRequest,
    session: Annotated[Session, Depends(get_db)],
):
    dist_map = {d.casefold(): d for d in BANGLADESH_64_DISTRICTS}
    origin_canon = normalize_name(request.origin).casefold()
    dest_canon = normalize_name(request.destination).casefold()

    origin_matched = dist_map.get(request.origin.strip().casefold()) or dist_map.get(origin_canon)
    dest_matched = dist_map.get(request.destination.strip().casefold()) or dist_map.get(dest_canon)

    if origin_matched:
        request.origin = origin_matched
    if dest_matched:
        request.destination = dest_matched

    supported = {
        name.casefold()
        for name in session.scalars(select(Location.name))
    }
    supported.update(dist_map.keys())

    if request.origin.casefold() not in supported and origin_canon not in supported:
        raise HTTPException(status_code=422, detail="Unsupported origin location. Please select one of the 64 districts.")
    if request.destination.casefold() not in supported and dest_canon not in supported:
        raise HTTPException(
            status_code=422, detail="Unsupported destination location. Please select one of the 64 districts."
        )
    res = search_routes(session, request)
    return res


@app.get("/api/timetables/bus", response_model=list[BusTimetableItem], tags=["Timetables"])
def bus_timetables(
    session: Annotated[Session, Depends(get_db)],
    travel_date: date = Query(default_factory=date.today),
    service: str | None = None,
    origin: str | None = None,
    destination: str | None = None,
):
    query = select(BusSchedule).order_by(BusSchedule.departure, BusSchedule.transport_name)
    if service:
        query = query.where(
            (BusSchedule.route_id.ilike(f"%{service.strip()}%"))
            | (BusSchedule.transport_name.ilike(f"%{service.strip()}%"))
        )
    if origin:
        query = query.where(BusSchedule.from_district.ilike(f"%{origin.strip()}%"))
    if destination:
        query = query.where(BusSchedule.to_district.ilike(f"%{destination.strip()}%"))
    return [
        BusTimetableItem(
            travel_date=travel_date,
            route_id=row.route_id,
            origin=row.from_district,
            destination=row.to_district,
            transport_name=row.transport_name,
            departure=row.departure,
            arrival=row.arrival,
            fare=row.fare if getattr(row, "fare", None) is not None else 0,
            fare_bdt=row.fare if getattr(row, "fare", None) is not None else 0,
        )
        for row in session.scalars(query.limit(200))
    ]


@app.get("/api/timetables/bus/{service_id}", response_model=list[BusTimetableItem], tags=["Timetables"])
def bus_timetable_by_id(
    service_id: str,
    session: Annotated[Session, Depends(get_db)],
    travel_date: date = Query(default_factory=date.today),
):
    rows = list(
        session.scalars(
            select(BusSchedule)
            .where(BusSchedule.route_id.ilike(service_id.strip()))
            .order_by(BusSchedule.departure)
        )
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Bus service not found")
    return [
        BusTimetableItem(
            travel_date=travel_date,
            route_id=row.route_id,
            origin=row.from_district,
            destination=row.to_district,
            transport_name=row.transport_name,
            departure=row.departure,
            arrival=row.arrival,
            fare=row.fare if getattr(row, "fare", None) is not None else 0,
            fare_bdt=row.fare if getattr(row, "fare", None) is not None else 0,
        )
        for row in rows
    ]


@app.get("/api/timetables/train", response_model=list[TrainTimetableItem], tags=["Timetables"])
def train_timetables(
    session: Annotated[Session, Depends(get_db)],
    travel_date: date = Query(default_factory=date.today),
    train_no: str | None = None,
    train_name: str | None = None,
    origin: str | None = None,
    destination: str | None = None,
):
    return train_timetable(
        session,
        travel_date,
        train_no=train_no,
        train_name=train_name,
        origin=origin,
        destination=destination,
    )


@app.get("/api/timetables/train/{train_no}", response_model=list[TrainTimetableItem], tags=["Timetables"])
def train_timetable_by_no(
    train_no: str,
    session: Annotated[Session, Depends(get_db)],
    travel_date: date = Query(default_factory=date.today),
):
    results = train_timetable(session, travel_date, train_no=train_no)
    if not results:
        raise HTTPException(status_code=404, detail="Train service not found")
    return results


@app.get("/api/timetables/local", response_model=list[LocalTransportItem], tags=["Timetables"])
def local_transport_timetables(
    session: Annotated[Session, Depends(get_db)],
    district: str | None = None,
    location: str | None = None,
):
    query = select(LocalEdge).order_by(LocalEdge.parent_district, LocalEdge.from_location)
    if district:
        query = query.where(LocalEdge.parent_district.ilike(f"%{district.strip()}%"))
    if location:
        loc = f"%{location.strip()}%"
        query = query.where(
            (LocalEdge.from_location.ilike(loc))
            | (LocalEdge.to_location.ilike(loc))
            | (LocalEdge.parent_district.ilike(loc))
        )
    rows = list(session.scalars(query.limit(200)))
    items = []
    for r in rows:
        duration = max(10, round(r.distance_km * 2.5))
        fare_min = max(20, round(20 + r.distance_km * 4))
        fare_max = max(50, round(30 + r.distance_km * 12))
        items.append(
            LocalTransportItem(
                id=r.id,
                from_location=r.from_location,
                to_location=r.to_location,
                parent_district=r.parent_district,
                distance_km=round(r.distance_km, 1),
                vehicle_types=["CNG Auto-Rickshaw", "Shared Easy Bike", "Feeder Shuttle / Minibus"],
                est_duration_minutes=duration,
                est_fare_min_bdt=fare_min,
                est_fare_max_bdt=fare_max,
                frequency="Continuous local dispatch (every 5-15 mins)",
            )
        )
    return items


# -------------------------------------------------------------
# Admin Endpoints (Section 3.2, 15)
# -------------------------------------------------------------

@app.get("/api/admin/districts", tags=["Admin"])
def admin_list_districts(
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    return list(session.scalars(select(District.name).order_by(District.name)))




@app.get("/api/admin/locations", tags=["Admin"])
def admin_list_locations(
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    return [
        {
            "name": row.name,
            "kind": row.kind,
            "district_name": row.district_name,
        }
        for row in session.scalars(select(Location).order_by(Location.name))
    ]




@app.get("/api/admin/district-edges", tags=["Admin"])
def admin_list_district_edges(
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    return [
        {
            "id": row.id,
            "from_district": row.from_district,
            "to_district": row.to_district,
            "distance_km": row.distance_km,
        }
        for row in session.scalars(select(DistrictEdge).order_by(DistrictEdge.from_district))
    ]


@app.get("/api/admin/local-edges", tags=["Admin"])
def admin_list_local_edges(
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    return [
        {
            "id": row.id,
            "from_location": row.from_location,
            "to_location": row.to_location,
            "distance_km": row.distance_km,
            "parent_district": row.parent_district,
        }
        for row in session.scalars(select(LocalEdge).order_by(LocalEdge.id))
    ]


@app.get("/api/admin/bus-schedules", tags=["Admin"])
def admin_list_bus_schedules(
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=500, ge=1, le=2000),
):
    return [
        {
            "id": row.id,
            "route_id": row.route_id,
            "from_district": row.from_district,
            "to_district": row.to_district,
            "transport_name": row.transport_name,
            "departure": row.departure,
            "arrival": row.arrival,
        }
        for row in session.scalars(select(BusSchedule).order_by(BusSchedule.id).limit(limit))
    ]


@app.post("/api/admin/bus-schedules", status_code=201, tags=["Admin"])
def admin_add_bus_schedule(
    body: BusScheduleInput,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    row = BusSchedule(**body.model_dump())
    session.add(row)
    commit_or_conflict(session)
    log_admin_action(
        session,
        actor=admin_user,
        action="CREATE_BUS_SCHEDULE",
        target_type="BusSchedule",
        target_id=str(row.id),
        details={"route_id": row.route_id, "from": row.from_district, "to": row.to_district},
    )
    session.commit()
    return {"id": row.id}


@app.put("/api/admin/bus-schedules/{schedule_id}", tags=["Admin"])
def admin_update_bus_schedule(
    schedule_id: int,
    body: BusScheduleInput,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    row = session.get(BusSchedule, schedule_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Bus schedule not found")
    row.route_id = body.route_id.strip()
    row.from_district = body.from_district.strip()
    row.to_district = body.to_district.strip()
    row.transport_name = body.transport_name.strip()
    row.departure = body.departure
    row.arrival = body.arrival
    row.fare = body.fare
    commit_or_conflict(session)
    log_admin_action(
        session,
        actor=admin_user,
        action="UPDATE_BUS_SCHEDULE",
        target_type="BusSchedule",
        target_id=str(row.id),
        details={"route_id": row.route_id},
    )
    session.commit()
    return {"id": row.id}


@app.delete("/api/admin/bus-schedules/{schedule_id}", status_code=204, tags=["Admin"])
def admin_delete_bus_schedule(
    schedule_id: int,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    row = session.get(BusSchedule, schedule_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Bus schedule not found")
    session.delete(row)
    commit_or_conflict(session)
    log_admin_action(
        session,
        actor=admin_user,
        action="DELETE_BUS_SCHEDULE",
        target_type="BusSchedule",
        target_id=str(schedule_id),
    )
    session.commit()
    return Response(status_code=204)


@app.get("/api/admin/train-services", tags=["Admin"])
def admin_list_train_services(
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    return [
        {
            "id": row.id,
            "train_no": row.train_no,
            "train_name": row.train_name,
            "from_district": row.from_district,
            "to_district": row.to_district,
            "off_day": row.off_day,
            "departure": row.departure,
            "arrival": row.arrival,
            "day_offset": row.day_offset,
        }
        for row in session.scalars(select(TrainService).order_by(TrainService.train_no))
    ]


@app.post("/api/admin/train-services", status_code=201, tags=["Admin"])
def admin_add_train_service(
    body: TrainServiceInput,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    row = TrainService(**body.model_dump())
    session.add(row)
    commit_or_conflict(session)
    log_admin_action(
        session,
        actor=admin_user,
        action="CREATE_TRAIN_SERVICE",
        target_type="TrainService",
        target_id=str(row.id),
        details={"train_no": row.train_no, "name": row.train_name},
    )
    session.commit()
    return {"id": row.id}


@app.put("/api/admin/train-services/{service_id}", tags=["Admin"])
def admin_update_train_service(
    service_id: int,
    body: TrainServiceInput,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    row = session.get(TrainService, service_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Train service not found")
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    commit_or_conflict(session)
    log_admin_action(
        session,
        actor=admin_user,
        action="UPDATE_TRAIN_SERVICE",
        target_type="TrainService",
        target_id=str(row.id),
        details={"train_no": row.train_no},
    )
    session.commit()
    return {"id": row.id}


@app.delete("/api/admin/train-services/{service_id}", status_code=204, tags=["Admin"])
def admin_delete_train_service(
    service_id: int,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    row = session.get(TrainService, service_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Train service not found")
    session.delete(row)
    commit_or_conflict(session)
    log_admin_action(
        session,
        actor=admin_user,
        action="DELETE_TRAIN_SERVICE",
        target_type="TrainService",
        target_id=str(service_id),
    )
    session.commit()
    return Response(status_code=204)


@app.get("/api/admin/train-stops", tags=["Admin"])
def admin_list_train_stops(
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=500, ge=1, le=2000),
):
    return [
        {
            "id": row.id,
            "train_no": row.train_no,
            "train_name": row.train_name,
            "stop_order": row.stop_order,
            "station": row.station,
            "district_name": row.district_name,
            "arrival": row.arrival,
            "departure": row.departure,
            "day_offset": row.day_offset,
            "cumulative_km": row.cumulative_km,
        }
        for row in session.scalars(
            select(TrainStop)
            .order_by(TrainStop.train_no, TrainStop.stop_order)
            .limit(limit)
        )
    ]


@app.post("/api/admin/train-stops", status_code=201, tags=["Admin"])
def admin_add_train_stop(
    body: TrainStopInput,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    row = TrainStop(**body.model_dump())
    session.add(row)
    commit_or_conflict(session)
    log_admin_action(
        session,
        actor=admin_user,
        action="CREATE_TRAIN_STOP",
        target_type="TrainStop",
        target_id=str(row.id),
        details={"train_no": row.train_no, "station": row.station},
    )
    session.commit()
    return {"id": row.id}


@app.put("/api/admin/train-stops/{stop_id}", tags=["Admin"])
def admin_update_train_stop(
    stop_id: int,
    body: TrainStopInput,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    row = session.get(TrainStop, stop_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Train stop not found")
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    commit_or_conflict(session)
    log_admin_action(
        session,
        actor=admin_user,
        action="UPDATE_TRAIN_STOP",
        target_type="TrainStop",
        target_id=str(row.id),
        details={"train_no": row.train_no, "station": row.station},
    )
    session.commit()
    return {"id": row.id}


@app.delete("/api/admin/train-stops/{stop_id}", status_code=204, tags=["Admin"])
def admin_delete_train_stop(
    stop_id: int,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    row = session.get(TrainStop, stop_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Train stop not found")
    session.delete(row)
    commit_or_conflict(session)
    log_admin_action(
        session,
        actor=admin_user,
        action="DELETE_TRAIN_STOP",
        target_type="TrainStop",
        target_id=str(stop_id),
    )
    session.commit()
    return Response(status_code=204)


@app.get("/api/admin/config", tags=["Admin"])
def admin_get_config(
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    return [
        {"key": row.key, "value": row.value}
        for row in session.scalars(select(RoutingConfig).order_by(RoutingConfig.key))
    ]


@app.put("/api/admin/config/{key}", tags=["Admin"])
def admin_set_config(
    key: str,
    body: RoutingConfigInput,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    if key != body.key:
        raise HTTPException(status_code=422, detail="Path parameter key must match body key")
    row = session.get(RoutingConfig, key)
    if row is None:
        row = RoutingConfig(key=key, value=body.value)
        session.add(row)
    else:
        row.value = body.value
    commit_or_conflict(session)
    log_admin_action(
        session,
        actor=admin_user,
        action="UPDATE_CONFIG",
        target_type="RoutingConfig",
        target_id=key,
    )
    session.commit()
    return {"key": row.key, "value": row.value}


@app.get("/api/admin/audit-logs", response_model=list[AuditLogResponse], tags=["Admin Audit Logs"])
def admin_list_audit_logs(
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    actor: str | None = None,
    action: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    query = select(AuditLog)
    if actor:
        query = query.where(AuditLog.actor == actor)
    if action:
        query = query.where(AuditLog.action == action)
    query = query.order_by(AuditLog.created_at.desc()).limit(limit)
    return list(session.scalars(query))


# -------------------------------------------------------------
# Admin User Reports Management (Section 3 & 6)
# -------------------------------------------------------------

@app.get("/api/admin/reports", response_model=list[AdminReportDetailResponse], tags=["Admin Reports"])
def admin_list_reports(
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    status: str | None = None,
    category: str | None = None,
    search: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    include_deleted: bool = False,
):
    """Lists submitted reports for admin review with filtering by status, category, date, and search keyword."""
    query = (
        select(UserReport, User.full_name, User.email)
        .join(User, UserReport.user_id == User.user_id, isouter=True)
    )

    if not include_deleted:
        query = query.where(UserReport.admin_deleted == False)

    if status and status.upper() != "ALL":
        query = query.where(func.upper(UserReport.status) == status.upper())

    if category:
        query = query.where(func.lower(UserReport.category) == category.strip().lower())

    if search:
        s = f"%{search.strip().lower()}%"
        query = query.where(
            func.lower(UserReport.report_id).like(s)
            | func.lower(UserReport.title).like(s)
            | func.lower(UserReport.description).like(s)
            | func.lower(UserReport.user_id).like(s)
            | func.lower(User.full_name).like(s)
            | func.lower(User.email).like(s)
        )

    if start_date:
        try:
            sd = datetime.fromisoformat(start_date)
            query = query.where(UserReport.submitted_at >= sd)
        except Exception:
            pass

    if end_date:
        try:
            ed = datetime.fromisoformat(end_date)
            query = query.where(UserReport.submitted_at <= ed)
        except Exception:
            pass

    query = query.order_by(UserReport.submitted_at.desc())
    results = session.execute(query).all()

    items = []
    for report, user_name, user_email in results:
        items.append(
            AdminReportDetailResponse(
                report_id=report.report_id,
                user_id=report.user_id,
                user_name=user_name,
                user_email=user_email,
                category=report.category,
                title=report.title,
                description=report.description,
                transport_mode=report.transport_mode,
                related_route_info=report.related_route_info,
                evidence_path=report.evidence_path,
                status=report.status,
                submitted_at=report.submitted_at,
                reviewed_by=report.reviewed_by,
                reviewed_at=report.reviewed_at,
                admin_response=report.admin_response,
                user_deleted=report.user_deleted,
                admin_deleted=report.admin_deleted,
            )
        )
    return items


@app.get("/api/admin/reports/{report_id}", response_model=AdminReportDetailResponse, tags=["Admin Reports"])
def admin_get_report(
    report_id: str,
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    """Retrieves full details for a specific user issue report."""
    row = session.execute(
        select(UserReport, User.full_name, User.email)
        .join(User, UserReport.user_id == User.user_id, isouter=True)
        .where(UserReport.report_id == report_id)
    ).first()

    if not row:
        raise HTTPException(status_code=404, detail="Report not found.")

    report, user_name, user_email = row
    return AdminReportDetailResponse(
        report_id=report.report_id,
        user_id=report.user_id,
        user_name=user_name,
        user_email=user_email,
        category=report.category,
        title=report.title,
        description=report.description,
        transport_mode=report.transport_mode,
        related_route_info=report.related_route_info,
        evidence_path=report.evidence_path,
        status=report.status,
        submitted_at=report.submitted_at,
        reviewed_by=report.reviewed_by,
        reviewed_at=report.reviewed_at,
        admin_response=report.admin_response,
        user_deleted=report.user_deleted,
        admin_deleted=report.admin_deleted,
    )


@app.post("/api/admin/reports/{report_id}/verify", response_model=AdminReportDetailResponse, tags=["Admin Reports"])
def admin_verify_report(
    report_id: str,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    body: AdminReportReviewRequest | None = None,
):
    """Verifies a user report, changes status to VERIFIED, and notifies the submitting user."""
    report = session.scalar(select(UserReport).where(UserReport.report_id == report_id))
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    prev_status = report.status
    report.status = "VERIFIED"
    report.reviewed_by = admin_user
    report.reviewed_at = datetime.now(timezone.utc)
    if body and body.admin_response:
        report.admin_response = body.admin_response.strip()

    # Prevent repeated identical notifications
    if prev_status != "VERIFIED":
        note_text = f" Note: {report.admin_response}" if report.admin_response else ""
        notif = Notification(
            user_id=report.user_id,
            report_id=report.report_id,
            title="Report Verified",
            message=f"Your report (ID: {report.report_id}) has been reviewed and verified by the administrator. Thank you for helping us improve SmartRoute BD.{note_text}",
            notification_type="REPORT_VERIFIED",
        )
        session.add(notif)

    log_admin_action(
        session,
        actor=admin_user,
        action="VERIFY_REPORT",
        target_type="UserReport",
        target_id=report.report_id,
        details={"status": "VERIFIED", "user_id": report.user_id, "admin_response": report.admin_response},
    )
    session.commit()
    session.refresh(report)

    user = session.scalar(select(User).where(User.user_id == report.user_id))
    return AdminReportDetailResponse(
        report_id=report.report_id,
        user_id=report.user_id,
        user_name=user.full_name if user else None,
        user_email=user.email if user else None,
        category=report.category,
        title=report.title,
        description=report.description,
        transport_mode=report.transport_mode,
        related_route_info=report.related_route_info,
        evidence_path=report.evidence_path,
        status=report.status,
        submitted_at=report.submitted_at,
        reviewed_by=report.reviewed_by,
        reviewed_at=report.reviewed_at,
        admin_response=report.admin_response,
        user_deleted=report.user_deleted,
        admin_deleted=report.admin_deleted,
    )


@app.post("/api/admin/reports/{report_id}/reject", response_model=AdminReportDetailResponse, tags=["Admin Reports"])
def admin_reject_report(
    report_id: str,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    body: AdminReportReviewRequest | None = None,
):
    """Rejects a user report, requires a rejection reason, and notifies the submitting user."""
    report = session.scalar(select(UserReport).where(UserReport.report_id == report_id))
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    rejection_reason = (body.admin_response or "").strip() if body else ""
    if not rejection_reason:
        raise HTTPException(
            status_code=422,
            detail="A rejection reason or explanation is required when rejecting a report.",
        )

    prev_status = report.status
    report.status = "REJECTED"
    report.reviewed_by = admin_user
    report.reviewed_at = datetime.now(timezone.utc)
    report.admin_response = rejection_reason

    # Prevent repeated identical notifications
    if prev_status != "REJECTED":
        notif = Notification(
            user_id=report.user_id,
            report_id=report.report_id,
            title="Report Rejected",
            message=f"Your report (ID: {report.report_id}) has been reviewed but could not be verified. Reason: {rejection_reason}.",
            notification_type="REPORT_REJECTED",
        )
        session.add(notif)

    log_admin_action(
        session,
        actor=admin_user,
        action="REJECT_REPORT",
        target_type="UserReport",
        target_id=report.report_id,
        details={"status": "REJECTED", "user_id": report.user_id, "reason": rejection_reason},
    )
    session.commit()
    session.refresh(report)

    user = session.scalar(select(User).where(User.user_id == report.user_id))
    return AdminReportDetailResponse(
        report_id=report.report_id,
        user_id=report.user_id,
        user_name=user.full_name if user else None,
        user_email=user.email if user else None,
        category=report.category,
        title=report.title,
        description=report.description,
        transport_mode=report.transport_mode,
        related_route_info=report.related_route_info,
        evidence_path=report.evidence_path,
        status=report.status,
        submitted_at=report.submitted_at,
        reviewed_by=report.reviewed_by,
        reviewed_at=report.reviewed_at,
        admin_response=report.admin_response,
        user_deleted=report.user_deleted,
        admin_deleted=report.admin_deleted,
    )


@app.delete("/api/admin/reports/{report_id}", tags=["Admin Reports"])
def admin_delete_report_from_history(
    report_id: str,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    """Soft-deletes a report from the admin visible history while preserving the audit record."""
    report = session.scalar(select(UserReport).where(UserReport.report_id == report_id))
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    report.admin_deleted = True
    log_admin_action(
        session,
        actor=admin_user,
        action="ADMIN_DELETE_REPORT_HISTORY",
        target_type="UserReport",
        target_id=report.report_id,
    )
    session.commit()
    return {"message": "Report removed from admin visible history."}


# -------------------------------------------------------------
# Admin User Warnings & User Blocking System (Section 7 & 8)
# -------------------------------------------------------------

@app.get("/api/admin/users", response_model=list[AdminUserSummaryResponse], tags=["Admin Users"])
def admin_list_users(
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    search: str | None = None,
    status_filter: str = "all",
):
    """Lists registered users with their blocking status, warning counts, and submitted report counts."""
    query = select(User).where(User.role != "admin")

    if status_filter == "blocked":
        query = query.where(User.is_blocked == True)
    elif status_filter == "active":
        query = query.where(User.is_blocked == False)

    if search:
        s = f"%{search.strip().lower()}%"
        query = query.where(
            func.lower(User.full_name).like(s)
            | func.lower(User.email).like(s)
            | func.lower(User.user_id).like(s)
        )

    query = query.order_by(User.created_at.desc())
    users = list(session.scalars(query))

    result = []
    for u in users:
        rep_count = session.scalar(
            select(func.count(UserReport.id)).where(UserReport.user_id == u.user_id)
        ) or 0
        warn_count = session.scalar(
            select(func.count(UserWarning.id)).where(UserWarning.user_id == u.user_id)
        ) or 0

        result.append(
            AdminUserSummaryResponse(
                user_id=u.user_id,
                full_name=u.full_name,
                email=u.email,
                role=u.role,
                is_blocked=u.is_blocked,
                blocked_reason=u.blocked_reason,
                blocked_at=u.blocked_at,
                blocked_by=u.blocked_by,
                created_at=u.created_at,
                report_count=rep_count,
                warning_count=warn_count,
            )
        )

    if status_filter == "warned":
        result = [r for r in result if r.warning_count > 0]

    return result


@app.get("/api/admin/users/{user_id}", tags=["Admin Users"])
def admin_get_user_details(
    user_id: str,
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    """Retrieves full moderation details for a user (warnings, block history, and reports)."""
    user = session.scalar(select(User).where(User.user_id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    reports = list(session.scalars(select(UserReport).where(UserReport.user_id == user_id).order_by(UserReport.submitted_at.desc())))
    warnings = list(session.scalars(select(UserWarning).where(UserWarning.user_id == user_id).order_by(UserWarning.created_at.desc())))
    block_history = list(session.scalars(select(UserBlockHistory).where(UserBlockHistory.user_id == user_id).order_by(UserBlockHistory.created_at.desc())))

    return {
        "user_id": user.user_id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "is_blocked": user.is_blocked,
        "blocked_reason": user.blocked_reason,
        "blocked_at": user.blocked_at,
        "blocked_by": user.blocked_by,
        "created_at": user.created_at,
        "reports": reports,
        "warnings": warnings,
        "block_history": block_history,
    }


@app.post("/api/admin/users/{user_id}/warn", response_model=UserWarningResponse, status_code=status.HTTP_201_CREATED, tags=["Admin Users"])
def admin_issue_user_warning(
    user_id: str,
    body: UserWarningCreateRequest,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    """Issues an official warning to a user and generates a warning notification."""
    user = session.scalar(select(User).where(User.user_id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    reason = body.reason.strip()
    warning = UserWarning(
        user_id=user.user_id,
        admin_id=admin_user,
        reason=reason,
    )
    session.add(warning)

    notif = Notification(
        user_id=user.user_id,
        title="Administrative Warning",
        message=f"Warning from SmartRoute BD Administration: Your reporting activity has violated our reporting guidelines. Reason: {reason}. Please use the reporting system responsibly.",
        notification_type="ADMIN_WARNING",
    )
    session.add(notif)

    log_admin_action(
        session,
        actor=admin_user,
        action="WARN_USER",
        target_type="User",
        target_id=user.user_id,
        details={"reason": reason},
    )
    session.commit()
    session.refresh(warning)
    return warning


@app.get("/api/admin/users/{user_id}/warnings", response_model=list[UserWarningResponse], tags=["Admin Users"])
def admin_get_user_warnings(
    user_id: str,
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    """Returns the list of administrative warnings issued to a user."""
    return list(session.scalars(select(UserWarning).where(UserWarning.user_id == user_id).order_by(UserWarning.created_at.desc())))


@app.post("/api/admin/users/{user_id}/block", tags=["Admin Users"])
def admin_block_user(
    user_id: str,
    body: UserBlockRequest,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    """Blocks a user from submitting reports and accessing protected actions."""
    user = session.scalar(select(User).where(User.user_id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Administrator accounts cannot be blocked.")

    reason = body.reason.strip()
    user.is_blocked = True
    user.blocked_reason = reason
    user.blocked_at = datetime.now(timezone.utc)
    user.blocked_by = admin_user

    history_entry = UserBlockHistory(
        user_id=user.user_id,
        admin_id=admin_user,
        action="BLOCK",
        reason=reason,
    )
    session.add(history_entry)

    notif = Notification(
        user_id=user.user_id,
        title="Account Suspended",
        message=f"Your account has been restricted by an administrator. Reason: {reason}.",
        notification_type="ACCOUNT_BLOCKED",
    )
    session.add(notif)

    log_admin_action(
        session,
        actor=admin_user,
        action="BLOCK_USER",
        target_type="User",
        target_id=user.user_id,
        details={"reason": reason},
    )
    session.commit()
    session.refresh(user)
    return {
        "message": f"User {user.user_id} has been blocked successfully.",
        "is_blocked": True,
        "reason": reason,
        "user": UserProfileResponse.model_validate(user),
    }


@app.post("/api/admin/users/{user_id}/unblock", tags=["Admin Users"])
def admin_unblock_user(
    user_id: str,
    admin_user: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    body: UserUnblockRequest | None = None,
):
    """Unblocks a previously restricted user account."""
    user = session.scalar(select(User).where(User.user_id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    reason = (body.reason.strip() if body and body.reason else "Unblocked by administrator.")
    user.is_blocked = False
    user.blocked_reason = None
    user.blocked_at = None
    user.blocked_by = None

    history_entry = UserBlockHistory(
        user_id=user.user_id,
        admin_id=admin_user,
        action="UNBLOCK",
        reason=reason,
    )
    session.add(history_entry)

    notif = Notification(
        user_id=user.user_id,
        title="Account Restriction Lifted",
        message=f"Your account restriction has been lifted by an administrator. Note: {reason}.",
        notification_type="ACCOUNT_RESTORED",
    )
    session.add(notif)

    log_admin_action(
        session,
        actor=admin_user,
        action="UNBLOCK_USER",
        target_type="User",
        target_id=user.user_id,
        details={"reason": reason},
    )
    session.commit()
    session.refresh(user)
    return {
        "message": f"User {user.user_id} has been unblocked successfully.",
        "is_blocked": False,
        "reason": reason,
        "user": UserProfileResponse.model_validate(user),
    }


@app.get("/api/admin/users/{user_id}/block-history", response_model=list[UserBlockHistoryResponse], tags=["Admin Users"])
def admin_get_user_block_history(
    user_id: str,
    _: Annotated[str, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
):
    """Returns the chronological blocking and unblocking history for a user."""
    return list(session.scalars(select(UserBlockHistory).where(UserBlockHistory.user_id == user_id).order_by(UserBlockHistory.created_at.desc())))

