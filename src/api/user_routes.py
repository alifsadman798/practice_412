import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from src.auth.security import (
    create_access_token,
    generate_report_id,
    generate_user_id,
    get_active_current_user,
    get_current_user,
    get_or_create_admin_user,
    hash_password,
    verify_password,
)
from src.database.connection import get_db
from src.database.models import (
    AuditLog,
    FavouriteRoute,
    FavouriteService,
    Notification,
    User,
    UserPreference,
    UserReport,
)
from src.api.user_schemas import (
    ChangePasswordRequest,
    FavouriteRouteInput,
    FavouriteRouteResponse,
    FavouriteServiceInput,
    FavouriteServiceResponse,
    NotificationResponse,
    ReportCreateRequest,
    ReportResponse,
    UnreadNotificationCountResponse,
    UserAuthResponse,
    UserLoginRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserPreferencesInput,
    UserPreferencesResponse,
    UserRegisterRequest,
)

router = APIRouter()


# -------------------------------------------------------------
# User Authentication Endpoints (Section 2)
# -------------------------------------------------------------

@router.post("/api/auth/register", response_model=UserAuthResponse, status_code=status.HTTP_201_CREATED, tags=["Auth"])
def register_user(
    body: UserRegisterRequest,
    session: Annotated[Session, Depends(get_db)],
):
    email = body.email.strip().lower()
    existing = session.scalar(select(User).where(func.lower(User.email) == email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists. Please log in.",
        )

    # Generate unique User ID (SRU-XXXXXXXX)
    user_id = generate_user_id()
    while session.scalar(select(User).where(User.user_id == user_id)):
        user_id = generate_user_id()

    hashed_pw = hash_password(body.password)
    user = User(
        user_id=user_id,
        full_name=body.full_name.strip(),
        email=email,
        password_hash=hashed_pw,
        role="user",
    )
    session.add(user)

    # Create default user preference
    pref = UserPreference(
        user_id=user_id,
        default_transport="No Preference",
        default_preference="balanced",
    )
    session.add(pref)
    session.commit()
    session.refresh(user)

    token = create_access_token({"sub": user.user_id, "email": user.email, "role": user.role})
    return UserAuthResponse(user=UserProfileResponse.model_validate(user), access_token=token)


@router.post("/api/auth/login", response_model=UserAuthResponse, tags=["Auth"])
def login_user(
    body: UserLoginRequest,
    session: Annotated[Session, Depends(get_db)],
):
    admin_user_env = os.getenv("ADMIN_USERNAME", "admin").strip().lower()
    admin_pass_env = os.getenv("ADMIN_PASSWORD", "12345678").strip()
    identifier = body.email.strip().lower()

    # Check if logging in as Admin with admin credentials
    if identifier in ("admin", "admin@smartroute.bd", admin_user_env) and body.password.strip() == admin_pass_env:
        admin_user = get_or_create_admin_user(session)
        token = create_access_token({"sub": admin_user.user_id, "email": admin_user.email, "role": "admin"})
        return UserAuthResponse(user=UserProfileResponse.model_validate(admin_user), access_token=token)

    user = session.scalar(select(User).where(func.lower(User.email) == identifier))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user.user_id, "email": user.email, "role": user.role})
    return UserAuthResponse(user=UserProfileResponse.model_validate(user), access_token=token)


@router.get("/api/auth/me", response_model=UserProfileResponse, tags=["Auth"])
def get_current_user_profile(
    user: Annotated[User, Depends(get_current_user)],
):
    return user


@router.put("/api/auth/profile", response_model=UserProfileResponse, tags=["Auth"])
def update_profile(
    body: UserProfileUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    user.full_name = body.full_name.strip()
    session.commit()
    session.refresh(user)
    return user


@router.put("/api/auth/change-password", tags=["Auth"])
def change_password(
    body: ChangePasswordRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password does not match our records.",
        )
    user.password_hash = hash_password(body.new_password)
    session.commit()
    return {"message": "Password changed successfully."}


# -------------------------------------------------------------
# User Preferences (Section 3.1)
# -------------------------------------------------------------

@router.get("/api/user/preferences", response_model=UserPreferencesResponse, tags=["Preferences"])
def get_preferences(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    pref = session.scalar(select(UserPreference).where(UserPreference.user_id == user.user_id))
    if not pref:
        pref = UserPreference(user_id=user.user_id, default_transport="No Preference", default_preference="balanced")
        session.add(pref)
        session.commit()
        session.refresh(pref)
    return pref


@router.put("/api/user/preferences", response_model=UserPreferencesResponse, tags=["Preferences"])
def update_preferences(
    body: UserPreferencesInput,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    pref = session.scalar(select(UserPreference).where(UserPreference.user_id == user.user_id))
    if not pref:
        pref = UserPreference(
            user_id=user.user_id,
            default_transport=body.default_transport,
            default_preference=body.default_preference,
        )
        session.add(pref)
    else:
        pref.default_transport = body.default_transport
        pref.default_preference = body.default_preference
    session.commit()
    session.refresh(pref)
    return pref


# -------------------------------------------------------------
# Favourite Routes & Services (Sections 3.2, 3.3)
# -------------------------------------------------------------

@router.get("/api/user/favourites/routes", response_model=list[FavouriteRouteResponse], tags=["Favourites"])
def list_favourite_routes(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    return list(session.scalars(select(FavouriteRoute).where(FavouriteRoute.user_id == user.user_id).order_by(FavouriteRoute.created_at.desc())))


@router.post("/api/user/favourites/routes", response_model=FavouriteRouteResponse, status_code=status.HTTP_201_CREATED, tags=["Favourites"])
def add_favourite_route(
    body: FavouriteRouteInput,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    origin = body.origin.strip()
    destination = body.destination.strip()
    existing = session.scalar(
        select(FavouriteRoute).where(
            FavouriteRoute.user_id == user.user_id,
            func.lower(FavouriteRoute.origin) == origin.lower(),
            func.lower(FavouriteRoute.destination) == destination.lower(),
        )
    )
    if existing:
        return existing

    route = FavouriteRoute(user_id=user.user_id, origin=origin, destination=destination)
    session.add(route)
    session.commit()
    session.refresh(route)
    return route


@router.delete("/api/user/favourites/routes/{route_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Favourites"])
def delete_favourite_route(
    route_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    row = session.get(FavouriteRoute, route_id)
    if row and row.user_id == user.user_id:
        session.delete(row)
        session.commit()
    return None


@router.get("/api/user/favourites/services", response_model=list[FavouriteServiceResponse], tags=["Favourites"])
def list_favourite_services(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    return list(session.scalars(select(FavouriteService).where(FavouriteService.user_id == user.user_id).order_by(FavouriteService.created_at.desc())))


@router.post("/api/user/favourites/services", response_model=FavouriteServiceResponse, status_code=status.HTTP_201_CREATED, tags=["Favourites"])
def add_favourite_service(
    body: FavouriteServiceInput,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    identifier = body.service_identifier.strip()
    existing = session.scalar(
        select(FavouriteService).where(
            FavouriteService.user_id == user.user_id,
            FavouriteService.transport_type == body.transport_type,
            FavouriteService.service_identifier == identifier,
        )
    )
    if existing:
        return existing

    fav = FavouriteService(
        user_id=user.user_id,
        transport_type=body.transport_type,
        service_identifier=identifier,
        service_name=body.service_name.strip(),
    )
    session.add(fav)
    session.commit()
    session.refresh(fav)
    return fav


@router.delete("/api/user/favourites/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Favourites"])
def delete_favourite_service(
    service_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    row = session.get(FavouriteService, service_id)
    if row and row.user_id == user.user_id:
        session.delete(row)
        session.commit()
    return None


# -------------------------------------------------------------
# User Issue Reporting & Complaint Management (Section 4 & 5)
# -------------------------------------------------------------

UPLOAD_DIR = Path("static/uploads/evidence")


@router.post("/api/user/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED, tags=["User Reports"])
def submit_report(
    body: ReportCreateRequest,
    user: Annotated[User, Depends(get_active_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    """Submits a new complaint/report. Blocked users are prohibited from submitting."""
    report_id = generate_report_id()
    while session.scalar(select(UserReport).where(UserReport.report_id == report_id)):
        report_id = generate_report_id()

    report = UserReport(
        report_id=report_id,
        user_id=user.user_id,
        category=body.category.strip(),
        title=body.title.strip(),
        description=body.description.strip(),
        transport_mode=body.transport_mode or "General",
        related_route_info=body.related_route_info.strip() if body.related_route_info else None,
        evidence_path=body.evidence_path.strip() if body.evidence_path else None,
        status="PENDING",
    )
    session.add(report)

    # Log audit entry
    session.add(
        AuditLog(
            actor=user.user_id,
            action="SUBMIT_REPORT",
            target_type="UserReport",
            target_id=report_id,
            details={"category": report.category, "title": report.title},
        )
    )

    session.commit()
    session.refresh(report)
    return report


@router.post("/api/user/reports/upload-evidence", tags=["User Reports"])
async def upload_report_evidence(
    user: Annotated[User, Depends(get_active_current_user)],
    file: UploadFile = File(...),
):
    """Safely accepts an image/PDF screenshot or evidence document for a report."""
    ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}
    ext = Path(file.filename or "evidence.jpg").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Allowed formats: PNG, JPG, JPEG, WEBP, PDF.",
        )

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 5MB maximum limit.",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_filename = f"{uuid.uuid4().hex[:12]}_{secrets.token_hex(4)}{ext}"
    target_path = UPLOAD_DIR / safe_filename
    with open(target_path, "wb") as f:
        f.write(content)

    return {"evidence_path": f"/static/uploads/evidence/{safe_filename}"}


@router.get("/api/user/reports", response_model=list[ReportResponse], tags=["User Reports"])
def list_user_reports(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    """Retrieves user's submitted reports that have not been soft-deleted from their history."""
    query = (
        select(UserReport)
        .where(UserReport.user_id == user.user_id, UserReport.user_deleted == False)
        .order_by(UserReport.submitted_at.desc())
    )
    return list(session.scalars(query))


@router.get("/api/user/reports/{report_id}", response_model=ReportResponse, tags=["User Reports"])
def get_user_report(
    report_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    """Retrieves single report details owned by the authenticated user."""
    report = session.scalar(
        select(UserReport).where(
            UserReport.report_id == report_id,
            UserReport.user_id == user.user_id,
            UserReport.user_deleted == False,
        )
    )
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found in your history.")
    return report


@router.delete("/api/user/reports/{report_id}", tags=["User Reports"])
def delete_report_from_user_history(
    report_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    """Soft-deletes a report from the user's visible history without deleting the admin review or audit records."""
    report = session.scalar(
        select(UserReport).where(
            UserReport.report_id == report_id,
            UserReport.user_id == user.user_id,
            UserReport.user_deleted == False,
        )
    )
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found in your history.")

    report.user_deleted = True
    session.add(
        AuditLog(
            actor=user.user_id,
            action="USER_DELETE_REPORT_HISTORY",
            target_type="UserReport",
            target_id=report_id,
            details={"user_id": user.user_id},
        )
    )
    session.commit()
    return {"message": "Report removed from your history."}


# -------------------------------------------------------------
# User Notifications Endpoints (Section 4)
# -------------------------------------------------------------

@router.get("/api/user/notifications", response_model=list[NotificationResponse], tags=["Notifications"])
def list_user_notifications(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    """Lists notifications for the authenticated user in reverse chronological order."""
    query = (
        select(Notification)
        .where(Notification.user_id == user.user_id)
        .order_by(Notification.created_at.desc())
    )
    return list(session.scalars(query))


@router.get("/api/user/notifications/unread-count", response_model=UnreadNotificationCountResponse, tags=["Notifications"])
def get_unread_notification_count(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    """Returns the count of unread notifications for the user."""
    count = session.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.user_id,
            Notification.is_read == False,
        )
    ) or 0
    return UnreadNotificationCountResponse(unread_count=count)


@router.put("/api/user/notifications/{notification_id}/read", response_model=NotificationResponse, tags=["Notifications"])
def mark_notification_as_read(
    notification_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    """Marks a single notification as read."""
    notif = session.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.user_id,
        )
    )
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    notif.is_read = True
    session.commit()
    session.refresh(notif)
    return notif


@router.put("/api/user/notifications/mark-all-read", tags=["Notifications"])
def mark_all_notifications_as_read(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
):
    """Marks all notifications for the user as read."""
    session.execute(
        update(Notification)
        .where(Notification.user_id == user.user_id, Notification.is_read == False)
        .values(is_read=True)
    )
    session.commit()
    return {"message": "All notifications marked as read."}


