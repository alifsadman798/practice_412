import argparse
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from src.database.connection import SessionLocal
from src.database.models import (
    BusSchedule,
    District,
    DistrictEdge,
    LocalEdge,
    Location,
    RoutingConfig,
    TrainService,
    TrainStop,
)
from src.data.loader import (
    parse_day_offset,
    parse_float_km,
    parse_time,
    positive_distance,
    read_csv,
    required_text,
)
from src.data.normalize import normalize_name
from src.shared.constants import CORE_CITIES, MAJOR_CITIES, TRAFFIC_FACTORS


def build_station_district_resolver(
    districts: set[str], local_edges_data: list[dict[str, str]]
):
    resolver: dict[str, str] = {}
    lower_districts = {d.casefold(): d for d in districts}

    for d in districts:
        resolver[d] = d

    for row in local_edges_data:
        parent = normalize_name(row.get("Parent_District", "").strip())
        from_loc = row.get("From", "").strip()
        to_loc = row.get("To", "").strip()
        if parent:
            if from_loc and from_loc not in resolver:
                resolver[from_loc] = parent
            if to_loc and to_loc not in resolver:
                resolver[to_loc] = parent

    def resolve(station: str) -> str:
        canon_station = normalize_name(station)
        if station in resolver:
            return resolver[station]
        if canon_station in resolver:
            return resolver[canon_station]
        if station.casefold() in lower_districts:
            return lower_districts[station.casefold()]
        if canon_station.casefold() in lower_districts:
            return lower_districts[canon_station.casefold()]
        for d in sorted(districts, key=len, reverse=True):
            if d.casefold() in station.casefold() or d.casefold() in canon_station.casefold():
                return d
        return "Dhaka"

    return resolve


def seed_database(session: Session, data_dir: Path, force: bool = False) -> dict[str, int]:
    has_records = any(
        session.scalar(select(func.count()).select_from(model)) for model in (
            District, DistrictEdge, LocalEdge, BusSchedule, TrainService, TrainStop, RoutingConfig
        )
    )

    if has_records:
        if not force:
            raise RuntimeError(
                "Transport data already exists; refusing to overwrite admin-maintained data (pass --force to re-seed)."
            )
        # Clear existing tables in exact reverse dependency order
        session.execute(delete(TrainStop))
        session.execute(delete(TrainService))
        session.execute(delete(BusSchedule))
        session.execute(delete(LocalEdge))
        session.execute(delete(DistrictEdge))
        session.execute(delete(Location))
        session.execute(delete(District))
        session.execute(delete(RoutingConfig))
        session.flush()

    district_edges_data = read_csv(data_dir, "64_districts.csv", ("32_districts.csv",))
    local_edges_data = read_csv(data_dir, "local_distance.csv")
    buses_data = read_csv(data_dir, "bus_schedule_64_district_with_fares.csv", ("bus_schedule_64_district.csv", "bus_schedules.csv"))
    trains_data = read_csv(data_dir, "train_routes_final.csv", ("train_routes.csv",))
    stops_data = read_csv(data_dir, "train_stops.csv")

    # 1. Collect all unique districts across all datasets
    districts = set()
    for row in district_edges_data:
        districts.add(normalize_name(required_text(row, "From", "districts")))
        districts.add(normalize_name(required_text(row, "To", "districts")))
    for row in buses_data:
        districts.add(normalize_name(required_text(row, "From", "bus_schedules")))
        districts.add(normalize_name(required_text(row, "To", "bus_schedules")))
    for row in local_edges_data:
        districts.add(normalize_name(required_text(row, "Parent_District", "local_distance.csv")))
    for row in trains_data:
        districts.add(normalize_name(required_text(row, "From_District", "train_routes.csv")))
        districts.add(normalize_name(required_text(row, "To_District", "train_routes.csv")))
    for row in stops_data:
        d = row.get("District", "").strip()
        if d:
            districts.add(normalize_name(d))

    resolve_station = build_station_district_resolver(districts, local_edges_data)

    # Insert Districts
    for district_name in sorted(districts):
        session.add(District(name=district_name))
    session.flush()

    # Collect Locations in dictionary to guarantee primary key uniqueness
    locations_dict: dict[str, Location] = {}
    for district_name in sorted(districts):
        locations_dict[district_name] = Location(
            name=district_name, kind="district", district_name=district_name
        )

    for row in local_edges_data:
        parent = normalize_name(required_text(row, "Parent_District", "local_distance.csv"))
        for loc in (
            required_text(row, "From", "local_distance.csv"),
            required_text(row, "To", "local_distance.csv"),
        ):
            if loc not in locations_dict:
                locations_dict[loc] = Location(name=loc, kind="upazila", district_name=parent)

    for row in stops_data:
        station = required_text(row, "Station", "train_stops.csv")
        raw_dist = row.get("District", "").strip()
        dist = normalize_name(raw_dist) if raw_dist else resolve_station(station)
        if station not in locations_dict:
            locations_dict[station] = Location(name=station, kind="station", district_name=dist)
        elif locations_dict[station].kind == "upazila":
            locations_dict[station].kind = "station"

    session.add_all(locations_dict.values())
    session.flush()

    # 3. District Edges (Undirected, canonical ordered)
    seen_district_edges = set()
    for row in district_edges_data:
        from_district = normalize_name(required_text(row, "From", "districts"))
        to_district = normalize_name(required_text(row, "To", "districts"))
        distance = positive_distance(row, "districts")
        ordered_from, ordered_to = sorted((from_district, to_district))
        key = (ordered_from, ordered_to)
        if key not in seen_district_edges:
            seen_district_edges.add(key)
            session.add(
                DistrictEdge(
                    from_district=ordered_from,
                    to_district=ordered_to,
                    distance_km=distance,
                )
            )
    session.flush()

    # 4. Local Edges (Only edges with positive distance and distinct endpoints)
    seen_local_edges = set()
    for row in local_edges_data:
        from_loc = required_text(row, "From", "local_distance.csv")
        to_loc = required_text(row, "To", "local_distance.csv")
        parent = normalize_name(required_text(row, "Parent_District", "local_distance.csv"))
        try:
            distance = float(row.get("Distance_km", 0))
        except (ValueError, TypeError):
            continue
        if distance <= 0 or from_loc.casefold() == to_loc.casefold():
            continue
        key = (from_loc, to_loc)
        if key not in seen_local_edges:
            seen_local_edges.add(key)
            session.add(
                LocalEdge(
                    from_location=from_loc,
                    to_location=to_loc,
                    distance_km=distance,
                    parent_district=parent,
                )
            )
    session.flush()

    # 5. Bus Schedules
    seen_bus_schedules = set()
    for row in buses_data:
        route_id = required_text(row, "Route_ID", "bus_schedules")
        from_district = normalize_name(required_text(row, "From", "bus_schedules"))
        to_district = normalize_name(required_text(row, "To", "bus_schedules"))
        transport = required_text(row, "Transport_Name", "bus_schedules")
        departure = parse_time(
            required_text(row, "Departure", "bus_schedules"),
            "bus_schedules",
        )
        arrival = parse_time(
            required_text(row, "Arrival", "bus_schedules"),
            "bus_schedules",
        )
        raw_fare = row.get("Fare", "0").strip()
        fare = int(float(raw_fare)) if raw_fare else 0
        key = (route_id, from_district, to_district, transport, departure, arrival)
        if key not in seen_bus_schedules:
            seen_bus_schedules.add(key)
            session.add(
                BusSchedule(
                    route_id=route_id,
                    from_district=from_district,
                    to_district=to_district,
                    transport_name=transport,
                    departure=departure,
                    arrival=arrival,
                    fare=fare,
                )
            )
    session.flush()

    # 6. Train Services
    seen_train_routes = set()
    for row in trains_data:
        train_no = required_text(row, "Train_No", "train_routes")
        if train_no in seen_train_routes:
            continue
        seen_train_routes.add(train_no)
        session.add(
            TrainService(
                train_no=train_no,
                train_name=required_text(row, "Train_Name", "train_routes"),
                from_district=normalize_name(required_text(row, "From_District", "train_routes")),
                to_district=normalize_name(required_text(row, "To_District", "train_routes")),
                off_day=required_text(row, "Off_Day", "train_routes"),
                departure=parse_time(
                    required_text(row, "Departure", "train_routes"),
                    "train_routes",
                ),
                arrival=parse_time(
                    required_text(row, "Arrival", "train_routes"),
                    "train_routes",
                ),
                day_offset=parse_day_offset(row.get("Day_Offset")),
            )
        )
    session.flush()

    # 7. Train Stops
    for row in stops_data:
        station = required_text(row, "Station", "train_stops.csv")
        raw_dist = row.get("District", "").strip()
        dist = normalize_name(raw_dist) if raw_dist else resolve_station(station)
        session.add(
            TrainStop(
                train_no=required_text(row, "Train_No", "train_stops.csv"),
                train_name=required_text(row, "Train_Name", "train_stops.csv"),
                stop_order=int(required_text(row, "Stop_Order", "train_stops.csv")),
                station=station,
                district_name=dist,
                arrival=parse_time(row.get("Arrival"), "train_stops.csv", optional=True),
                departure=parse_time(row.get("Departure"), "train_stops.csv", optional=True),
                day_offset=parse_day_offset(row.get("Day_Offset")),
                cumulative_km=float(row.get("Cumulative_KM", 0.0) or 0.0),
            )
        )
    session.flush()

    # 8. Routing Configuration
    session.add(RoutingConfig(key="core_cities", value=sorted(CORE_CITIES)))
    session.add(RoutingConfig(key="major_cities", value=sorted(MAJOR_CITIES)))
    session.add(RoutingConfig(key="traffic_factors", value=TRAFFIC_FACTORS))
    session.flush()

    return {
        "districts": session.scalar(select(func.count()).select_from(District)),
        "locations": session.scalar(select(func.count()).select_from(Location)),
        "district_edges": session.scalar(select(func.count()).select_from(DistrictEdge)),
        "local_edges": session.scalar(select(func.count()).select_from(LocalEdge)),
        "bus_schedules": session.scalar(select(func.count()).select_from(BusSchedule)),
        "train_services": session.scalar(select(func.count()).select_from(TrainService)),
        "train_stops": session.scalar(select(func.count()).select_from(TrainStop)),
        "routing_configs": session.scalar(select(func.count()).select_from(RoutingConfig)),
    }


def main():
    parser = argparse.ArgumentParser(description="Seed the PostgreSQL transport database.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "data",
        help="Path to CSV datasets",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing data",
    )
    args = parser.parse_args()
    with SessionLocal() as session:
        counts = seed_database(session, args.data_dir, force=args.force)
        session.commit()
        print("Seeded successfully:", counts)


if __name__ == "__main__":
    main()
