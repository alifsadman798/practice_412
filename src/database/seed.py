import argparse
from collections import defaultdict
from datetime import time
from pathlib import Path
import re

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
    districts: set[str],
    local_edges_data: list[dict[str, str]],
    district_edges_data: list[dict[str, str]] | None = None,
):
    lower_districts = {d.casefold(): d for d in districts}
    district_word_patterns = [
        (re.compile(r"\b" + re.escape(d) + r"\b", re.IGNORECASE), d)
        for d in sorted(districts, key=len, reverse=True)
    ]

    # Station -> candidate Parent_Districts from local_edges_data
    station_parents: dict[str, set[str]] = defaultdict(set)
    for row in local_edges_data:
        parent_raw = row.get("Parent_District", "").strip()
        if not parent_raw:
            continue
        parent = normalize_name(parent_raw)
        if parent in districts:
            for endpoint in (row.get("From", "").strip(), row.get("To", "").strip()):
                if endpoint:
                    station_parents[endpoint.casefold()].add(parent)
                    canon_endpoint = normalize_name(endpoint)
                    if canon_endpoint:
                        station_parents[canon_endpoint.casefold()].add(parent)

    # District adjacency graph from district_edges_data
    district_adjacency: dict[str, set[str]] = defaultdict(set)
    if district_edges_data:
        for row in district_edges_data:
            f_d = normalize_name(row.get("From", "").strip())
            t_d = normalize_name(row.get("To", "").strip())
            if f_d in districts and t_d in districts:
                district_adjacency[f_d].add(t_d)
                district_adjacency[t_d].add(f_d)

    def _match_direct(name: str) -> str | None:
        clean = name.strip()
        canon = normalize_name(clean)
        # Priority 1A: Exact case-insensitive match with official district
        if clean in districts:
            return clean
        if canon in districts:
            return canon
        if clean.casefold() in lower_districts:
            return lower_districts[clean.casefold()]
        if canon.casefold() in lower_districts:
            return lower_districts[canon.casefold()]
        # Priority 1B: Unambiguous full district-name match within longer station label
        matched_words = {
            d
            for pattern, d in district_word_patterns
            if pattern.search(clean) or pattern.search(canon)
        }
        if len(matched_words) == 1:
            return next(iter(matched_words))
        return None

    def _disambiguate_with_train_context(
        station: str,
        train_no: str,
        stop_order: int,
        stop_idx: int,
        train_stops: list[dict[str, str]],
        candidates: set[str],
    ) -> str:
        scores: dict[str, int] = {c: 0 for c in candidates}
        n_stops = len(train_stops)
        # Examine immediately preceding and following stops outward along train sequence
        for delta in [1, -1, 2, -2, 3, -3]:
            nb_idx = stop_idx + delta
            if 0 <= nb_idx < n_stops:
                nb = train_stops[nb_idx]
                nb_st = nb.get("Station", "").strip()
                nb_raw_d = nb.get("District", "").strip()
                if nb_raw_d:
                    nb_dist = normalize_name(nb_raw_d)
                else:
                    nb_dist = _match_direct(nb_st)
                    if not nb_dist:
                        nb_cand = station_parents.get(nb_st.casefold()) or station_parents.get(
                            normalize_name(nb_st).casefold()
                        )
                        if nb_cand and len(nb_cand) == 1:
                            nb_dist = next(iter(nb_cand))
                if nb_dist:
                    for c in candidates:
                        if nb_dist == c or normalize_name(nb_st) == c:
                            scores[c] += 10 // abs(delta)
                        elif c in district_adjacency.get(nb_dist, set()):
                            scores[c] += 5 // abs(delta)

        max_score = max(scores.values())
        if max_score > 0:
            winners = [c for c, sc in scores.items() if sc == max_score]
            if len(winners) == 1:
                return winners[0]

        raise ValueError(
            f"Cannot resolve ambiguous railway station '{station}' for train '{train_no}' "
            f"at stop order {stop_order}. Candidate districts: {sorted(candidates)}"
        )

    def resolve(
        station: str,
        *,
        train_no: str | None = None,
        stop_order: int | None = None,
        stop_idx: int | None = None,
        train_stops: list[dict[str, str]] | None = None,
    ) -> str:
        clean = station.strip()
        if not clean:
            raise ValueError("Railway station name cannot be blank.")

        # Priority 1: Match station name with official district name (exact or word boundary)
        direct = _match_direct(clean)
        if direct:
            return direct

        # Priority 2: Use local_distance.csv mapping
        canon = normalize_name(clean)
        candidates = (
            station_parents.get(clean.casefold())
            or station_parents.get(canon.casefold())
            or set()
        )

        if len(candidates) == 1:
            return next(iter(candidates))

        if len(candidates) > 1:
            # Priority 3 / Disambiguation: Examine train-stop sequence
            if train_stops is not None and stop_idx is not None and train_no is not None:
                return _disambiguate_with_train_context(
                    clean,
                    train_no,
                    stop_order or (stop_idx + 1),
                    stop_idx,
                    train_stops,
                    candidates,
                )
            raise ValueError(
                f"Ambiguous railway station '{clean}': multiple candidate districts {sorted(candidates)}. "
                f"Train context required for disambiguation."
            )

        # Missing / unknown station: Never default to Dhaka!
        raise ValueError(
            f"Cannot resolve railway station '{clean}' to an official district: mapping missing or unknown."
        )

    return resolve


def seed_database(session: Session, data_dir: Path, force: bool = False) -> dict[str, int]:
    # 1. Read all datasets first
    district_edges_data = read_csv(data_dir, "64_districts.csv", ("32_districts.csv",))
    local_edges_data = read_csv(data_dir, "local_distance.csv")
    buses_data = read_csv(
        data_dir,
        "bus_schedule_64_district_with_fares.csv",
        ("bus_schedule_64_district.csv", "bus_schedules.csv"),
    )
    trains_data = read_csv(data_dir, "train_routes_final.csv", ("train_routes.csv",))
    stops_data = read_csv(data_dir, "train_stops.csv")

    # 2. Collect official 64 districts exclusively from 64_districts.csv
    districts = set()
    for row in district_edges_data:
        districts.add(normalize_name(required_text(row, "From", "64_districts.csv")))
        districts.add(normalize_name(required_text(row, "To", "64_districts.csv")))

    if len(districts) != 64:
        raise ValueError(
            f"Expected exactly 64 official districts from 64_districts.csv, found {len(districts)}"
        )

    # 3. Validate other dataset references against official 64 districts
    for row in buses_data:
        f = normalize_name(required_text(row, "From", "bus_schedule_64_district_with_fares.csv"))
        t = normalize_name(required_text(row, "To", "bus_schedule_64_district_with_fares.csv"))
        if f not in districts:
            raise ValueError(
                f"bus_schedule_64_district_with_fares.csv: invalid From district '{row.get('From')}'"
            )
        if t not in districts:
            raise ValueError(
                f"bus_schedule_64_district_with_fares.csv: invalid To district '{row.get('To')}'"
            )

    for row in local_edges_data:
        parent = normalize_name(required_text(row, "Parent_District", "local_distance.csv"))
        if parent not in districts:
            raise ValueError(
                f"local_distance.csv: invalid Parent_District '{row.get('Parent_District')}'"
            )

    for row in stops_data:
        raw_d = row.get("District", "").strip()
        if raw_d:
            norm_d = normalize_name(raw_d)
            if norm_d not in districts:
                raise ValueError(
                    f"train_stops.csv: invalid District '{raw_d}' for station '{row.get('Station')}'"
                )

    # 4. Station resolver & pre-resolve train routes and stops before destructive actions
    resolve_station = build_station_district_resolver(
        districts, local_edges_data, district_edges_data
    )

    resolved_train_routes: list[dict[str, object]] = []
    seen_train_routes = set()
    for row in trains_data:
        train_no = required_text(row, "Train_No", "train_routes")
        if train_no in seen_train_routes:
            continue
        seen_train_routes.add(train_no)
        from_st = required_text(row, "From_District", "train_routes")
        to_st = required_text(row, "To_District", "train_routes")
        from_dist = resolve_station(from_st)
        to_dist = resolve_station(to_st)
        if from_dist not in districts:
            raise ValueError(
                f"train_routes: unresolvable From_District '{from_st}' for train '{train_no}'"
            )
        if to_dist not in districts:
            raise ValueError(
                f"train_routes: unresolvable To_District '{to_st}' for train '{train_no}'"
            )
        resolved_train_routes.append(
            {
                "train_no": train_no,
                "train_name": required_text(row, "Train_Name", "train_routes"),
                "from_district": from_dist,
                "to_district": to_dist,
                "off_day": required_text(row, "Off_Day", "train_routes"),
                "departure": parse_time(
                    required_text(row, "Departure", "train_routes"), "train_routes"
                ),
                "arrival": parse_time(
                    required_text(row, "Arrival", "train_routes"), "train_routes"
                ),
                "day_offset": parse_day_offset(row.get("Day_Offset")),
            }
        )

    train_stops_by_no: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in stops_data:
        train_stops_by_no[required_text(row, "Train_No", "train_stops.csv")].append(row)

    resolved_train_stops: list[dict[str, object]] = []
    for train_no, t_stops in train_stops_by_no.items():
        for idx, row in enumerate(t_stops):
            station = required_text(row, "Station", "train_stops.csv")
            stop_order = int(required_text(row, "Stop_Order", "train_stops.csv"))
            raw_dist = row.get("District", "").strip()
            if raw_dist:
                dist = normalize_name(raw_dist)
            else:
                dist = resolve_station(
                    station,
                    train_no=train_no,
                    stop_order=stop_order,
                    stop_idx=idx,
                    train_stops=t_stops,
                )
            if dist not in districts:
                raise ValueError(
                    f"train_stops.csv: unresolvable station '{station}' for train '{train_no}'"
                )
            resolved_train_stops.append(
                {
                    "train_no": train_no,
                    "train_name": required_text(row, "Train_Name", "train_stops.csv"),
                    "stop_order": stop_order,
                    "station": station,
                    "district_name": dist,
                    "arrival": parse_time(row.get("Arrival"), "train_stops.csv", optional=True),
                    "departure": parse_time(
                        row.get("Departure"), "train_stops.csv", optional=True
                    ),
                    "day_offset": parse_day_offset(row.get("Day_Offset")),
                    "cumulative_km": float(row.get("Cumulative_KM", 0.0) or 0.0),
                }
            )

    # 5. Pre-seeding checks and transactional safety
    has_records = any(
        session.scalar(select(func.count()).select_from(model))
        for model in (
            District,
            DistrictEdge,
            LocalEdge,
            BusSchedule,
            TrainService,
            TrainStop,
            RoutingConfig,
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

    # 6. Populate database
    # Insert Districts (strictly official 64 districts)
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

    for item in resolved_train_stops:
        station = str(item["station"])
        dist = str(item["district_name"])
        if station not in locations_dict:
            locations_dict[station] = Location(name=station, kind="station", district_name=dist)
        elif locations_dict[station].kind == "upazila":
            locations_dict[station].kind = "station"

    session.add_all(locations_dict.values())
    session.flush()

    # District Edges (Undirected, canonical ordered)
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

    # Local Edges (Only edges with positive distance and distinct endpoints)
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

    # Bus Schedules
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

    # Train Services (Endpoints resolved to official districts)
    for srv_dict in resolved_train_routes:
        session.add(TrainService(**srv_dict))
    session.flush()

    # Train Stops (District names strictly official districts)
    for stop_dict in resolved_train_stops:
        session.add(TrainStop(**stop_dict))
    session.flush()

    # Routing Configuration
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
