from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import District, LocalEdge, Location


def resolve_location(session: Session, name: str) -> tuple[str | None, str | None]:
    """Returns (district_name, station_name)."""
    norm = name.strip().casefold()
    districts = {d.name.casefold(): d.name for d in session.scalars(select(District))}
    if norm in districts:
        return districts[norm], None

    locations = {loc.name.casefold(): loc for loc in session.scalars(select(Location))}
    if norm in locations:
        loc = locations[norm]
        if loc.kind == "station":
            return loc.district_name, loc.name
        if loc.kind == "district":
            return loc.district_name or loc.name, None
        if loc.kind == "upazila":
            return loc.district_name, None

    local_edge = session.scalar(
        select(LocalEdge).where(LocalEdge.from_location.ilike(name.strip())).limit(1)
    )
    if local_edge:
        return local_edge.parent_district, None

    return None, None
