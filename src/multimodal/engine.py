from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from src.database.models import BusSchedule, DistrictEdge, TrainService, TrainStop
from src.data.graph import shortest_path
from src.bus.router import bus_trip, load_bus_network
from src.train.router import load_train_network, train_trip
from src.multimodal.combiner import combine_segments
from src.shared.constants import (
    LOCAL_FARE_BDT,
    LOCAL_SPEED_KMH,
    TRAIN_TRANSFER_BUFFER_MINUTES,
)
from src.shared.models import (
    Confidence,
    Leg,
    Mode,
    RouteKind,
    RouteOption,
    TimeRange,
)

_combine = combine_segments
MAX_TRANSFER_WAIT_MINUTES = 240
MAX_DETOUR_RATIO = 1.35


def _combine_with_local(
    first_opt: RouteOption | None,
    second_opt: RouteOption | None,
    first_leg: Leg | None,
    second_leg: Leg | None,
    interchange: str,
    path_nodes: list[str],
    transfer_wait: int,
    warning_text: str,
) -> RouteOption:
    legs = []
    if first_opt:
        if first_opt.legs and first_opt.path and not first_opt.legs[0].path:
            first_opt.legs[0].path = first_opt.path
        legs.extend(first_opt.legs)
        first_travel = first_opt.travel_time.expected_minutes
        first_min = first_opt.travel_time.minimum_minutes
        first_max = first_opt.travel_time.maximum_minutes
        first_wait = first_opt.waiting_minutes
        first_fare = first_opt.fare_bdt
        first_dist = first_opt.distance_km
        first_warn = first_opt.warnings
    else:
        if first_leg and not first_leg.path:
            first_leg.path = [first_leg.origin, first_leg.destination]
        legs.append(first_leg)
        first_travel = first_leg.travel_minutes
        first_min = first_leg.travel_minutes
        first_max = first_leg.travel_minutes
        first_wait = 0
        first_fare = first_leg.fare_bdt
        first_dist = first_leg.distance_km
        first_warn = []

    if second_opt:
        if second_opt.legs and second_opt.path and not second_opt.legs[0].path:
            second_opt.legs[0].path = second_opt.path
        legs.extend(second_opt.legs)
        second_travel = second_opt.travel_time.expected_minutes
        second_min = second_opt.travel_time.minimum_minutes
        second_max = second_opt.travel_time.maximum_minutes
        second_wait = second_opt.waiting_minutes
        second_fare = second_opt.fare_bdt
        second_dist = second_opt.distance_km
        second_warn = second_opt.warnings
    else:
        if second_leg and not second_leg.path:
            second_leg.path = [second_leg.origin, second_leg.destination]
        legs.append(second_leg)
        second_travel = second_leg.travel_minutes
        second_min = second_leg.travel_minutes
        second_max = second_leg.travel_minutes
        second_wait = 0
        second_fare = second_leg.fare_bdt
        second_dist = second_leg.distance_km
        second_warn = []

    warnings = list(dict.fromkeys(first_warn + second_warn + [warning_text]))
    clean_path = [
        name
        for idx, name in enumerate(path_nodes)
        if idx == 0 or name.casefold() != path_nodes[idx - 1].casefold()
    ]
    return RouteOption(
        kind=RouteKind.MULTIMODAL,
        path=clean_path,
        legs=legs,
        distance_km=round(first_dist + second_dist, 2),
        fare_bdt=first_fare + second_fare,
        travel_time=TimeRange(
            minimum_minutes=first_min + second_min + transfer_wait,
            expected_minutes=first_travel + second_travel + transfer_wait,
            maximum_minutes=first_max + second_max + transfer_wait,
        ),
        waiting_minutes=first_wait + second_wait + transfer_wait,
        transfers=1,
        confidence=Confidence.MEDIUM,
        warnings=warnings,
    )


def multimodal_trips(
    session: Session,
    origin: str,
    destination: str,
    requested: datetime,
    origin_station: str | None = None,
    destination_station: str | None = None,
    district_edges: list[DistrictEdge] | None = None,
    schedules_by_pair: dict[tuple[str, str], list[BusSchedule]] | None = None,
    train_services: list[TrainService] | None = None,
    stops_by_train: dict[str, list[TrainStop]] | None = None,
) -> list[RouteOption]:
    if district_edges is None or schedules_by_pair is None:
        district_edges, schedules_by_pair = load_bus_network(session)
    if train_services is None or stops_by_train is None:
        train_services, stops_by_train = load_train_network(session)

    # Establish baseline direct distance to avoid nonsensical geographic detours
    direct_route = shortest_path(district_edges, origin, destination)
    if direct_route is None or direct_route[1] <= 0:
        return []
    direct_dist = direct_route[1]

    stops = [stop for train_stops in stops_by_train.values() for stop in train_stops]
    train_districts = sorted(
        {stop.district_name for stop in stops},
        key=str.casefold,
    )
    candidate_interchanges = [
        d for d in train_districts if d not in (origin, destination)
    ]

    # Filter interchanges: must make positive progress along the natural travel corridor
    # Rejects absurd detours (e.g. visiting Rajshahi or Sylhet when traveling Dhaka -> Chattogram)
    sensible_interchanges: list[str] = []
    for ic in candidate_interchanges:
        p1 = shortest_path(district_edges, origin, ic)
        p2 = shortest_path(district_edges, ic, destination)
        if not p1 or not p2:
            continue
        d1, d2 = p1[1], p2[1]
        if d1 < direct_dist and d2 < direct_dist and (d1 + d2) <= MAX_DETOUR_RATIO * direct_dist:
            sensible_interchanges.append(ic)

    results: list[RouteOption] = []
    buffer = timedelta(minutes=TRAIN_TRANSFER_BUFFER_MINUTES)
    max_wait = timedelta(minutes=MAX_TRANSFER_WAIT_MINUTES)

    # 1. Standard Scheduled Interchanges (Bus+Train and Train+Bus along the corridor)
    for interchange in sensible_interchanges:
        # Option A: Bus to interchange, then Train to destination
        first_bus = bus_trip(
            session,
            origin,
            interchange,
            requested,
            district_edges,
            schedules_by_pair,
        )
        if first_bus:
            bus_option, _, bus_arrival = first_bus
            if bus_option.waiting_minutes <= MAX_TRANSFER_WAIT_MINUTES:
                train = train_trip(
                    session,
                    interchange,
                    destination,
                    bus_arrival + buffer,
                    destination_station=destination_station,
                    services=train_services,
                    stops_by_train=stops_by_train,
                )
                if train:
                    train_option, train_departure, train_arrival = train
                    transfer_wait = train_departure - bus_arrival
                    if buffer <= transfer_wait <= max_wait:
                        combined = _combine(
                            bus_option,
                            train_option,
                            interchange,
                            bus_arrival,
                            train_departure,
                        )
                        if combined.distance_km <= MAX_DETOUR_RATIO * direct_dist:
                            results.append(combined)

        # Option B: Train to interchange, then Bus to destination
        first_train = train_trip(
            session,
            origin,
            interchange,
            requested,
            origin_station=origin_station,
            services=train_services,
            stops_by_train=stops_by_train,
        )
        if first_train:
            train_option, _, train_arrival = first_train
            if train_option.waiting_minutes <= MAX_TRANSFER_WAIT_MINUTES:
                bus = bus_trip(
                    session,
                    interchange,
                    destination,
                    train_arrival + buffer,
                    district_edges,
                    schedules_by_pair,
                )
                if bus:
                    bus_option, bus_departure, _ = bus
                    transfer_wait = bus_departure - train_arrival
                    if buffer <= transfer_wait <= max_wait:
                        combined = _combine(
                            train_option,
                            bus_option,
                            interchange,
                            train_arrival,
                            bus_departure,
                        )
                        if combined.distance_km <= MAX_DETOUR_RATIO * direct_dist:
                            results.append(combined)

    # 2. Nearest-Station Connections (e.g. for destinations or origins without direct railway service)
    # Case A: Train from origin to nearest station to destination, then Bus / Local Transport to destination
    for r in candidate_interchanges:
        p_r_dest = shortest_path(district_edges, r, destination)
        p_orig_r = shortest_path(district_edges, origin, r)
        if not p_r_dest or not p_orig_r:
            continue
        d_orig_r, d_r_dest = p_orig_r[1], p_r_dest[1]
        if d_r_dest < direct_dist and (d_orig_r + d_r_dest) <= MAX_DETOUR_RATIO * direct_dist:
            first_train = train_trip(
                session,
                origin,
                r,
                requested,
                origin_station=origin_station,
                services=train_services,
                stops_by_train=stops_by_train,
            )
            if first_train:
                train_option, _, train_arrival = first_train
                # Check scheduled bus
                bus = bus_trip(
                    session,
                    r,
                    destination,
                    train_arrival + buffer,
                    district_edges,
                    schedules_by_pair,
                )
                if bus:
                    bus_option, bus_departure, _ = bus
                    transfer_wait = bus_departure - train_arrival
                    if buffer <= transfer_wait <= max_wait:
                        combined = _combine(
                            train_option,
                            bus_option,
                            r,
                            train_arrival,
                            bus_departure,
                        )
                        results.append(combined)
                else:
                    # Direct bus not scheduled: use Local Transport as requested
                    local_time = round(d_r_dest / LOCAL_SPEED_KMH * 60)
                    local_fare = round(LOCAL_FARE_BDT + 1.5 * d_r_dest)
                    local_leg = Leg(
                        mode=Mode.LOCAL,
                        origin=r,
                        destination=destination,
                        service=f"Local transport / Regional bus ({r} to {destination})",
                        distance_km=d_r_dest,
                        fare_bdt=local_fare,
                        travel_minutes=local_time,
                        waiting_minutes=30,
                        path=p_r_dest[0],
                    )
                    dest_p = p_r_dest[0]
                    if dest_p and train_option.path and train_option.path[-1].casefold() == dest_p[0].casefold():
                        dest_p = dest_p[1:]
                    combined_local = _combine_with_local(
                        first_opt=train_option,
                        second_opt=None,
                        first_leg=None,
                        second_leg=local_leg,
                        interchange=r,
                        path_nodes=train_option.path + dest_p,
                        transfer_wait=30,
                        warning_text=f"Direct bus schedule not published from {r} to {destination}. Take local transport / regional service (approx. {local_time} mins).",
                    )
                    results.append(combined_local)

    # Case B: Reverse Case: Origin has no train; Bus / Local Transport to nearest station, then Train to destination
    for r in candidate_interchanges:
        p_orig_r = shortest_path(district_edges, origin, r)
        p_r_dest = shortest_path(district_edges, r, destination)
        if not p_orig_r or not p_r_dest:
            continue
        d_orig_r, d_r_dest = p_orig_r[1], p_r_dest[1]
        if d_orig_r < direct_dist and (d_orig_r + d_r_dest) <= MAX_DETOUR_RATIO * direct_dist:
            # Check scheduled bus from origin to r
            bus = bus_trip(
                session,
                origin,
                r,
                requested,
                district_edges,
                schedules_by_pair,
            )
            if bus:
                bus_option, _, bus_arrival = bus
                train = train_trip(
                    session,
                    r,
                    destination,
                    bus_arrival + buffer,
                    destination_station=destination_station,
                    services=train_services,
                    stops_by_train=stops_by_train,
                )
                if train:
                    train_option, train_departure, _ = train
                    transfer_wait = train_departure - bus_arrival
                    if buffer <= transfer_wait <= max_wait:
                        combined = _combine(
                            bus_option,
                            train_option,
                            r,
                            bus_arrival,
                            train_departure,
                        )
                        results.append(combined)
            else:
                # No bus from origin to r: use Local Transport to reach railway station
                local_time = round(d_orig_r / LOCAL_SPEED_KMH * 60)
                local_arr = requested + timedelta(minutes=local_time)
                train = train_trip(
                    session,
                    r,
                    destination,
                    local_arr + buffer,
                    destination_station=destination_station,
                    services=train_services,
                    stops_by_train=stops_by_train,
                )
                if train:
                    train_option, train_departure, _ = train
                    transfer_wait = max(0, int((train_departure - local_arr).total_seconds() // 60))
                    if buffer.total_seconds() // 60 <= transfer_wait <= MAX_TRANSFER_WAIT_MINUTES:
                        local_fare = round(LOCAL_FARE_BDT + 1.5 * d_orig_r)
                        local_leg = Leg(
                            mode=Mode.LOCAL,
                            origin=origin,
                            destination=r,
                            service=f"Local transport / Regional bus ({origin} to {r})",
                            distance_km=d_orig_r,
                            fare_bdt=local_fare,
                            travel_minutes=local_time,
                            waiting_minutes=0,
                            path=p_orig_r[0],
                        )
                        train_p = train_option.path
                        if train_p and p_orig_r[0] and train_p[0].casefold() == p_orig_r[0][-1].casefold():
                            train_p = train_p[1:]
                        combined_local = _combine_with_local(
                            first_opt=None,
                            second_opt=train_option,
                            first_leg=local_leg,
                            second_leg=None,
                            interchange=r,
                            path_nodes=p_orig_r[0] + train_p,
                            transfer_wait=transfer_wait,
                            warning_text=f"Take local transport or regional bus from {origin} to {r} railway station (approx. {local_time} mins).",
                        )
                        results.append(combined_local)

    unique: dict[tuple, RouteOption] = {}
    for route in results:
        # Reject routes with loops/cycles (e.g., revisiting the same district)
        if len(route.path) != len(set(route.path)):
            continue
        # Reject routes where destination appears before the final stop
        if destination in route.path[:-1]:
            continue
        # Reject routes that exceed maximum detour ratio
        if route.distance_km > MAX_DETOUR_RATIO * direct_dist:
            continue
        identity = (
            tuple((leg.mode.value, leg.origin, leg.destination, leg.service) for leg in route.legs),
            tuple(route.path),
        )
        unique[identity] = route
    return list(unique.values())
