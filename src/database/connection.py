import os
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("Set DATABASE_URL to a PostgreSQL connection URL")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    if not (url.startswith("postgresql+psycopg://") or url.startswith("sqlite")):
        raise ValueError("DATABASE_URL must use the postgresql+psycopg:// scheme")
    return url


def get_engine():
    raw_url = database_url()
    if raw_url.startswith("postgresql"):
        # Ensure gssencmode=disable to prevent Windows SSPI/GSSAPI connection blocks
        url_obj = make_url(raw_url)
        query = dict(url_obj.query)
        if "gssencmode" not in query:
            query["gssencmode"] = "disable"
            url_obj = url_obj.set(query=query)
        return create_engine(url_obj, pool_pre_ping=True)
    return create_engine(raw_url, pool_pre_ping=True)


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
