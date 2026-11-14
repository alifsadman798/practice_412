from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import District, Location
from src.api.orchestrator import search_routes
from src.shared.models import RouteSearchRequest, RouteSearchResponse

api_router = APIRouter(prefix="/api", tags=["Routing"])


@api_router.get("/districts", response_model=list[str])
def get_districts(session: Annotated[Session, Depends(get_db)]):
    return list(session.scalars(select(District.name).order_by(District.name)))


@api_router.get("/locations")
def get_locations(session: Annotated[Session, Depends(get_db)]):
    return [
        {
            "name": row.name,
            "kind": row.kind,
            "district_name": row.district_name,
        }
        for row in session.scalars(select(Location).order_by(Location.name))
    ]


@api_router.post("/search", response_model=RouteSearchResponse)
def post_search(
    request: RouteSearchRequest,
    session: Annotated[Session, Depends(get_db)],
):
    return search_routes(session, request)
