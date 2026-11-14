from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import BusSchedule, DistrictEdge, RoutingConfig
from src.data.graph import shortest_path
from src.bus.fare import bus_fare
from src.bus.time import estimated_bus_minutes
from src.bus.waiting import next_bus_departure
from src.shared.constants import CORE_CITIES, MAJOR_CITIES, TRAFFIC_FACTORS
from src.shared.models import Confidence, Leg, Mode, RouteKind, RouteOption, TimeRange


def load_bus_network(
    session: Session,
) -> tuple[list[DistrictEdge], dict[tuple[str, str], list[BusSchedule]]]:
    edges = list(session.scalars(select(DistrictEdge)))
    schedules_by_pair: dict[tuple[str, str], list[BusSchedule]] = defaultdict(list)
    for schedule in session.scalars(
        select(BusSchedule).order_by(BusSchedule.departure, BusSchedule.transport_name)
    ):
        schedules_by_pair[(schedule.from_district, schedule.to_district)].append(
            schedule
        )
    return edges, dict(schedules_by_pair)


_next_bus = next_bus_departure


def bus_trip(
    session: Session,
    origin: str,
    destination: str,
    requested: datetime,
    district_edges: list[DistrictEdge] | None = None,
    schedules_by_pair: dict[tuple[str, str], list[BusSchedule]] | None = None,
) -> tuple[RouteOption, datetime, datetime] | None:
    if origin == destination:
        return None
    if district_edges is None or schedules_by_pair is None:
        district_edges, schedules_by_pair = load_bus_network(session)
    path_data = shortest_path(district_edges, origin, destination)
    scheduled = _next_bus(
        schedules_by_pair.get((origin, destination), []), requested
    )
    if path_data is None or scheduled is None:
        return None
    path, distance = path_data
    service, departure, arrival, waiting = scheduled
    actual_minutes = int((arrival - departure).total_seconds() // 60)
    config = {
        row.key: row.value
        for row in session.scalars(
            select(RoutingConfig).where(
                RoutingConfig.key.in_(
                    ("core_cities", "major_cities", "traffic_factors")
                )
            )
        )
    }
    core_cities = set(config.get("core_cities", CORE_CITIES))
    major_cities = set(config.get("major_cities", MAJOR_CITIES))
    traffic_factors = config.get("traffic_factors", TRAFFIC_FACTORS)
    expected = estimated_bus_minutes(
        distance,
        path,
        departure.time(),
        major_cities=major_cities,
        traffic_factors=traffic_factors,
    )
    fare = int(service.fare) if getattr(service, "fare", None) is not None else 0
    option = RouteOption(
        kind=RouteKind.BUS,
        path=path,
        legs=[
            Leg(
                mode=Mode.BUS,
                origin=origin,
                destination=destination,
                service=service.transport_name,
                departure_time=service.departure,
                arrival_time=service.arrival,
                distance_km=distance,
                fare_bdt=fare,
                travel_minutes=actual_minutes,
                waiting_minutes=waiting,
                path=path,
            )
        ],
        distance_km=distance,
        fare_bdt=fare,
        travel_time=TimeRange(
            minimum_minutes=round(expected * 0.85),
            expected_minutes=expected,
            maximum_minutes=round(expected * 1.2),
        ),
        waiting_minutes=waiting,
        transfers=0,
        confidence=Confidence.MEDIUM,
        warnings=[
            "Bus time range is a manual estimate, not live traffic data.",
            "The listed service times are schedules; real-time availability is not verified.",
        ],
    )
    return option, departure, arrival
