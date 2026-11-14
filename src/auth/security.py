import base64
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBasic, HTTPBasicCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import User, UserPreference

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "smartroute-bd-secure-jwt-secret-key-2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

bearer_scheme = HTTPBearer(auto_error=False)
security = HTTPBasic(auto_error=False)


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


def hash_password(password: str) -> str:
    """Hashes a plain text password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def generate_user_id() -> str:
    """Generates a unique User ID like SRU-7F3A91C2."""
    return f"SRU-{secrets.token_hex(4).upper()}"


def generate_report_id() -> str:
    """Generates a unique Report ID like REP-7F3A91C2."""
    return f"REP-{secrets.token_hex(4).upper()}"


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Creates a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Decodes and validates a JWT access token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except (jwt.PyJWTError, Exception):
        return None


def get_or_create_admin_user(session: Session) -> User:
    """Ensures a corresponding administrator User entity exists in the database for full user capability."""
    admin_username = os.getenv("ADMIN_USERNAME", "admin").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "12345678").strip()
    admin_user = session.scalar(
        select(User).where(
            (User.user_id == "SRU-ADMIN")
            | (func.lower(User.email) == "admin@smartroute.bd")
            | (func.lower(User.email) == admin_username.lower())
        )
    )
    if not admin_user:
        admin_user = User(
            user_id="SRU-ADMIN",
            full_name="System Administrator",
            email="admin@smartroute.bd",
            password_hash=hash_password(admin_password),
            role="admin",
        )
        session.add(admin_user)
        session.flush()
        pref = UserPreference(
            user_id=admin_user.user_id,
            default_transport="No Preference",
            default_preference="balanced",
        )
        session.add(pref)
        session.commit()
        session.refresh(admin_user)
    else:
        needs_commit = False
        if admin_user.role != "admin":
            admin_user.role = "admin"
            needs_commit = True
        if not verify_password(admin_password, admin_user.password_hash):
            admin_user.password_hash = hash_password(admin_password)
            needs_commit = True
        if needs_commit:
            session.commit()
            session.refresh(admin_user)

    return admin_user


def get_current_user_optional(
    request: Request,
    auth: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    session: Annotated[Session, Depends(get_db)],
) -> User | None:
    """Extracts the authenticated user if a valid bearer token or basic auth is provided; otherwise returns None."""
    if auth and auth.credentials:
        payload = decode_access_token(auth.credentials)
        if payload and "sub" in payload:
            user_id = payload["sub"]
            user = session.scalar(select(User).where(User.user_id == user_id))
            if user:
                return user

    # Allow Basic Auth for administrator to seamlessly access user endpoints
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Basic "):
        try:
            b64_val = auth_header[6:].strip()
            decoded = base64.b64decode(b64_val).decode("utf-8")
            if ":" in decoded:
                u, p = decoded.split(":", 1)
                admin_username = os.getenv("ADMIN_USERNAME", "admin").strip()
                admin_password = os.getenv("ADMIN_PASSWORD", "12345678").strip()
                if secrets.compare_digest(u, admin_username) and secrets.compare_digest(p, admin_password):
                    return get_or_create_admin_user(session)
        except Exception:
            pass

    return None


def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    """Requires an authenticated user, raising 401 Unauthorized if not signed in."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in to access this feature.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_active_current_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Verifies that the authenticated user account is active and not blocked by an administrator."""
    if user.is_blocked:
        reason = user.blocked_reason or "Account restricted by administrator."
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your account has been restricted by an administrator. Reason: {reason}. You cannot perform this action.",
        )
    return user
