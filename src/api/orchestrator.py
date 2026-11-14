from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import District, LocalEdge, Location
from src.data.graph import shortest_path
from src.data.normalize import normalize_location_lookup, normalize_name
from src.bus.router import bus_trip, load_bus_network
from src.train.router import load_train_network, train_trip
from src.multimodal.engine import multimodal_trips
from src.api.comparison import build_comparison
from src.shared.constants import (
    LOCAL_FARE_BDT,
    LOCAL_SPEED_KMH,
    LOCAL_TRANSFER_BUFFER_MINUTES,
)
from src.shared.models import (
    Comparison,
    Confidence,
    Leg,
    Mode,
    Preference,
    RouteKind,
    RouteOption,
    RouteSearchRequest,
    RouteSearchResponse,
    TimeRange,
)

_comparison = build_comparison


def _find_transfer_distance_and_time(
    from_name: str,
    to_name: str,
    local_edges_list: list[LocalEdge],
    district_edges_map,
) -> tuple[float, int]:
    f = from_name.strip().casefold()
    t = to_name.strip().casefold()
    if f == t:
        return 0.0, 0
    # 1. Direct local edge match
    for edge in local_edges_list:
        ef = edge.from_location.strip().casefold()
        et = edge.to_location.strip().casefold()
        if (ef == f and et == t) or (ef == t and et == f):
            d = float(edge.distance_km)
            return d, max(10, round(d / 30.0 * 60))
    # 2. Check if one is a station whose parent_district is the other
    for edge in local_edges_list:
        ef = edge.from_location.strip().casefold()
        ep = edge.parent_district.strip().casefold()
        if (ef == f and ep == t) or (ef == t and ep == f):
            d = float(edge.distance_km)
            return d, max(10, round(d / 30.0 * 60))
    # 3. Check shortest path in district_edges
    path_res = shortest_path(district_edges_map, from_name, to_name)
    if path_res and path_res[1] > 0:
        d = float(path_res[1])
        return d, max(15, round(d / 35.0 * 60))
    # 4. Fallback reasonable transfer
    return 20.0, 40


def _parse_time_to_minutes(t_val) -> int | None:
    if not t_val:
        return None
    s = str(t_val)[:5]
    try:
        parts = s.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return None


def _format_minutes_to_time(m: int) -> str:
    m = ((m % 1440) + 1440) % 1440
    return f"{m // 60:02d}:{m % 60:02d}"


def _format_loc_name(name: str, mode: Mode) -> str:
    n = name.strip()
    nl = n.lower()
    if mode == Mode.TRAIN:
        if "station" not in nl and "junction" not in nl and "halt" not in nl and "bypass" not in nl:
            return f"{n} Railway Station"
        return n
    elif mode == Mode.BUS:
        if "bus" not in nl and "terminal" not in nl and "stand" not in nl:
            return f"{n} Bus Terminal"
        return n
    return n


def _populate_route_time_metrics(r: RouteOption) -> None:
    first_leg = r.legs[0] if r.legs else None
    if first_leg:
        raw_dep = getattr(first_leg, "departure", None) or getattr(first_leg, "departure_time", None)
        dep_str = str(raw_dep)[:5] if raw_dep else None
        r.initial_waiting_minutes = getattr(first_leg, "waiting_minutes", 0) or 0
        r.next_departure_time = dep_str
        r.next_departure_service = first_leg.service
        r.next_departure_mode = first_leg.mode.value if hasattr(first_leg.mode, "value") else str(first_leg.mode)
        r.next_departure_location = _format_loc_name(first_leg.origin, first_leg.mode)
    else:
        r.initial_waiting_minutes = 0

    r.in_journey_minutes = r.travel_time.expected_minutes
    r.total_journey_minutes = r.travel_time.expected_minutes + (r.initial_waiting_minutes or 0)


def _attach_transfer_guidance(
    routes: list[RouteOption],
    local_edges_list: list[LocalEdge],
    district_edges_map,
) -> None:
    for route in routes:
        if len(route.legs) < 2:
            continue
        for idx in range(len(route.legs) - 1):
            cur = route.legs[idx]
            nxt = route.legs[idx + 1]
            diff_places = cur.destination.strip().casefold() != nxt.origin.strip().casefold()
            diff_modes = cur.mode != nxt.mode

            if diff_places or diff_modes:
                f_raw = cur.destination.strip()
                t_raw = nxt.origin.strip()
                f_name = _format_loc_name(f_raw, cur.mode)
                t_name = _format_loc_name(t_raw, nxt.mode)

                if diff_places:
                    dist_km, travel_mins = _find_transfer_distance_and_time(
                        f_raw, t_raw, local_edges_list, district_edges_map
                    )
                else:
                    dist_km = 5.0
                    travel_mins = 15

                nxt_dep = str(nxt.departure)[:5] if nxt.departure else (str(nxt.departure_time)[:5] if hasattr(nxt, "departure_time") and nxt.departure_time else None)
                cur_arr = str(cur.arrival)[:5] if cur.arrival else (str(cur.arrival_time)[:5] if hasattr(cur, "arrival_time") and cur.arrival_time else None)

                nxt_dep_mins = _parse_time_to_minutes(nxt_dep)
                cur_arr_mins = _parse_time_to_minutes(cur_arr)

                rec_leave_time = None
                if nxt_dep_mins is not None:
                    rec_leave_mins = nxt_dep_mins - travel_mins
                    rec_leave_time = _format_minutes_to_time(rec_leave_mins)

                ready_to_board_time = None
                if cur_arr_mins is not None:
                    ready_to_board_time = _format_minutes_to_time(cur_arr_mins + travel_mins)

                buffer_mins = None
                is_tight = False
                is_feasible = True
                if nxt_dep_mins is not None and cur_arr_mins is not None:
                    raw_diff = nxt_dep_mins - cur_arr_mins
                    if raw_diff < 0:
                        raw_diff += 1440
                    buffer_mins = raw_diff - travel_mins
                    is_tight = buffer_mins < 20
                    is_feasible = buffer_mins >= 0

                cur.transfer_to_next = {
                    "from_location": f_name,
                    "to_location": t_name,
                    "from_district": f_raw,
                    "to_district": t_raw,
                    "mode": "local",
                    "service": "Auto-rickshaw / CNG / Local shuttle",
                    "distance_km": round(dist_km, 1),
                    "travel_minutes": travel_mins,
                    "fare_bdt": 50 if dist_km <= 10 else round(50 + 1.5 * (dist_km - 10)),
                    "instruction": f"Use local transport (auto-rickshaw / CNG / local shuttle) from {f_name} to {t_name}.",
                    "target_arrival_time": nxt_dep,
                    "next_departure_time": nxt_dep,
                    "prev_arrival_time": cur_arr,
                    "ready_to_board_time": ready_to_board_time,
                    "station_waiting_minutes": buffer_mins,
                    "recommended_leave_time": rec_leave_time,
                    "buffer_minutes": buffer_mins,
                    "is_tight": is_tight,
                    "is_feasible": is_feasible,
                }
                warning_note = (
                    f"Connection Alert: Reach {t_name} before next {nxt.mode.value} departure "
                    f"(allow ~{travel_mins} mins for local transfer from {f_name}"
                    + (f", depart by {rec_leave_time}" if rec_leave_time else "")
                    + ")."
                )
                if warning_note not in route.warnings:
                    route.warnings.append(warning_note)


def search_routes(
    session: Session, request: RouteSearchRequest
) -> RouteSearchResponse:
    districts = {
        name.casefold(): name
        for name in session.scalars(select(District.name))
    }
    origin_raw_key = request.origin.strip().casefold()
    destination_raw_key = request.destination.strip().casefold()
    origin_canon = normalize_name(request.origin)
    destination_canon = normalize_name(request.destination)
    origin_key = origin_canon.casefold()
    destination_key = destination_canon.casefold()

    origin = districts.get(origin_key) or districts.get(origin_raw_key)
    destination = districts.get(destination_key) or districts.get(destination_raw_key)

    local_edges = list(
        session.scalars(select(LocalEdge).order_by(LocalEdge.id))
    )
    origin_edge = next(
        (
            edge
            for edge in local_edges
            if edge.from_location.casefold() in (origin_key, origin_raw_key)
        ),
        None,
    )
    destination_edge = next(
        (
            edge
            for edge in local_edges
            if edge.from_location.casefold() in (destination_key, destination_raw_key)
        ),
        None,
    )
    direct_local_edge = next(
        (
            edge
            for edge in local_edges
            if {edge.from_location.casefold(), edge.to_location.casefold()}
            <= {origin_key, destination_key, origin_raw_key, destination_raw_key}
        ),
        None,
    )
    location_records = {
        location.name.casefold(): location
        for location in session.scalars(select(Location))
    }
    origin_loc = location_records.get(origin_raw_key) or location_records.get(origin_key)
    dest_loc = location_records.get(destination_raw_key) or location_records.get(destination_key)

    origin_station = (
        request.origin
        if origin_loc and origin_loc.kind == "station"
        else None
    )
    destination_station = (
        request.destination
        if dest_loc and dest_loc.kind == "station"
        else None
    )
    if origin is None:
        origin = (
            origin_edge.parent_district
            if origin_edge
            else (
                origin_loc.district_name
                if origin_loc
                else None
            )
        )
    if destination is None:
        destination = (
            destination_edge.parent_district
            if destination_edge
            else (
                dest_loc.district_name
                if dest_loc
                else None
            )
        )

    def local_leg(edge: LocalEdge, from_location: str, to_location: str) -> Leg:
        return Leg(
            mode=Mode.LOCAL,
            origin=from_location,
            destination=to_location,
            service="Local transport (estimated)",
            distance_km=edge.distance_km,
            fare_bdt=LOCAL_FARE_BDT,
            travel_minutes=round(edge.distance_km / LOCAL_SPEED_KMH * 60),
            waiting_minutes=0,
            path=[from_location, to_location],
        )

    def direct_local_route(edge: LocalEdge) -> RouteOption:
        leg = local_leg(edge, request.origin, request.destination)
        return RouteOption(
            kind=RouteKind.MULTIMODAL,
            path=[request.origin, request.destination],
            legs=[leg],
            distance_km=leg.distance_km,
            fare_bdt=leg.fare_bdt,
            travel_time=TimeRange(
                minimum_minutes=max(1, round(leg.travel_minutes * 0.9)),
                expected_minutes=leg.travel_minutes,
                maximum_minutes=round(leg.travel_minutes * 1.25),
            ),
            waiting_minutes=0,
            transfers=0,
            confidence=Confidence.LOW,
            warnings=[
                "Local travel time uses the configured 30 km/h assumption; it is not a scheduled or live estimate."
            ],
        )

    if origin is None or destination is None:
        if direct_local_edge:
            route = direct_local_route(direct_local_edge)
            return RouteSearchResponse(
                routes=[route],
                comparison=_comparison([route]),
                direct_train_available=False,
                direct_train_message="No direct train available on this route.",
            )
        return RouteSearchResponse(
            routes=[],
            comparison=Comparison(note="No route: origin or destination is unsupported."),
            direct_train_available=False,
            direct_train_message="No direct train available on this route.",
        )

    requested = datetime.combine(request.travel_date, request.departure_time)
    district_edges, schedules_by_pair = load_bus_network(session)
    train_services, stops_by_train = load_train_network(session)
    routes: list[RouteOption] = []

    bus = bus_trip(
        session,
        origin,
        destination,
        requested,
        district_edges=district_edges,
        schedules_by_pair=schedules_by_pair,
    )
    if bus:
        routes.append(bus[0])

    train = train_trip(
        session,
        origin,
        destination,
        requested,
        origin_station=origin_station,
        destination_station=destination_station,
        services=train_services,
        stops_by_train=stops_by_train,
    )
    if train:
        routes.append(train[0])

    multimodal = multimodal_trips(
        session,
        origin,
        destination,
        requested,
        origin_station=origin_station,
        destination_station=destination_station,
        district_edges=district_edges,
        schedules_by_pair=schedules_by_pair,
        train_services=train_services,
        stops_by_train=stops_by_train,
    )

    best_multimodal: RouteOption | None = None
    if multimodal:
        for m in multimodal:
            _populate_route_time_metrics(m)
        # Strictly show a single multimodal path which is comparatively best according to user preference
        if request.preference == Preference.CHEAPEST:
            best_multimodal = min(
                multimodal,
                key=lambda r: (r.fare_bdt, r.total_journey_minutes if r.total_journey_minutes is not None else (r.travel_time.expected_minutes + r.waiting_minutes), r.distance_km),
            )
        elif request.preference == Preference.FASTEST:
            best_multimodal = min(
                multimodal,
                key=lambda r: (r.total_journey_minutes if r.total_journey_minutes is not None else (r.travel_time.expected_minutes + r.waiting_minutes), r.fare_bdt, r.distance_km),
            )
        elif request.preference == Preference.SHORTEST:
            best_multimodal = min(
                multimodal,
                key=lambda r: (r.distance_km, r.total_journey_minutes if r.total_journey_minutes is not None else (r.travel_time.expected_minutes + r.waiting_minutes), r.fare_bdt),
            )
        else:  # BALANCED or default
            best_multimodal = min(
                multimodal,
                key=lambda r: (r.total_journey_minutes if r.total_journey_minutes is not None else (r.travel_time.expected_minutes + r.waiting_minutes), r.fare_bdt, r.distance_km),
            )

    if best_multimodal is not None:
        routes.append(best_multimodal)

    origin_local = (
        local_leg(origin_edge, request.origin, origin_edge.to_location)
        if origin_edge and origin_edge.from_location.casefold() == origin_key
        else None
    )
    destination_local = (
        local_leg(destination_edge, destination_edge.to_location, request.destination)
        if destination_edge and destination_edge.from_location.casefold() == destination_key
        else None
    )

    results = routes
    if origin_local or destination_local:
        local_distance = sum(
            leg.distance_km
            for leg in (origin_local, destination_local)
            if leg is not None
        )
        local_time = sum(
            leg.travel_minutes
            for leg in (origin_local, destination_local)
            if leg is not None
        )
        local_fare = sum(
            leg.fare_bdt for leg in (origin_local, destination_local) if leg is not None
        )
        local_transfers = int(origin_local is not None) + int(
            destination_local is not None
        )
        transfer_buffers = LOCAL_TRANSFER_BUFFER_MINUTES * local_transfers
        for route in results:
            route.legs = (
                ([origin_local] if origin_local else [])
                + route.legs
                + ([destination_local] if destination_local else [])
            )
            combined_path = (
                (
                    [request.origin, origin_edge.to_location]
                    if origin_local and origin_edge
                    else []
                )
                + route.path
                + (
                    [destination_edge.to_location, request.destination]
                    if destination_local and destination_edge
                    else []
                )
            )
            route.path = [
                name
                for index, name in enumerate(combined_path)
                if index == 0
                or name.casefold() != combined_path[index - 1].casefold()
            ]
            route.distance_km = round(route.distance_km + local_distance, 2)
            route.fare_bdt += local_fare
            route.transfers += int(origin_local is not None) + int(
                destination_local is not None
            )
            route.waiting_minutes += transfer_buffers
            route.travel_time = TimeRange(
                minimum_minutes=route.travel_time.minimum_minutes
                + local_time
                + transfer_buffers,
                expected_minutes=route.travel_time.expected_minutes
                + local_time
                + transfer_buffers,
                maximum_minutes=route.travel_time.maximum_minutes
                + local_time
                + transfer_buffers,
            )
            route.kind = RouteKind.MULTIMODAL
            route.confidence = Confidence.LOW
            route.warnings.append(
                "Local travel time uses the configured 30 km/h assumption; it is not a scheduled or live estimate."
            )
        if origin.casefold() == destination.casefold():
            local_legs = [leg for leg in (origin_local, destination_local) if leg]
            local_transfers = max(0, len(local_legs) - 1)
            local_transfer_wait = LOCAL_TRANSFER_BUFFER_MINUTES * local_transfers
            local_path = [request.origin]
            if origin_edge:
                local_path.extend((origin_edge.to_location, origin))
            if destination_edge:
                local_path.extend(
                    (destination_edge.to_location, request.destination)
                )
            local_path = [
                name
                for index, name in enumerate(local_path)
                if index == 0 or name.casefold() != local_path[index - 1].casefold()
            ]
            results.append(
                RouteOption(
                    kind=RouteKind.MULTIMODAL,
                    path=local_path,
                    legs=local_legs,
                    distance_km=round(local_distance, 2),
                    fare_bdt=local_fare,
                    travel_time=TimeRange(
                        minimum_minutes=max(1, round((local_time + local_transfer_wait) * 0.9)),
                        expected_minutes=local_time + local_transfer_wait,
                        maximum_minutes=round((local_time + local_transfer_wait) * 1.25),
                    ),
                    waiting_minutes=local_transfer_wait,
                    transfers=local_transfers,
                    confidence=Confidence.LOW,
                    warnings=[
                        "Local travel time uses the configured 30 km/h assumption; it is not a scheduled or live estimate."
                    ],
                )
            )

    if direct_local_edge:
        results.append(direct_local_route(direct_local_edge))

    _attach_transfer_guidance(results, local_edges, district_edges)

    for r in results:
        _populate_route_time_metrics(r)

        # Dynamic Recommendation Reason
        if r.kind == RouteKind.TRAIN:
            r.recommendation_reason = f"🚆 Direct Train: Reliable non-stop railway connection from {origin} to {destination} with 0 transfers."
        elif r.kind == RouteKind.BUS:
            r.recommendation_reason = f"🚌 Direct Highway Bus: Direct highway travel without inter-station transfer."
        elif r.kind == RouteKind.MULTIMODAL:
            ic_name = r.legs[0].destination if r.legs else "Interchange"
            r.recommendation_reason = f"⚡ Multimodal Connection: Interchanges via {ic_name} with verified schedule buffer."

    if request.preference == Preference.CHEAPEST:
        results.sort(key=lambda route: (route.fare_bdt, route.total_journey_minutes if route.total_journey_minutes is not None else route.travel_time.expected_minutes))
    elif request.preference == Preference.FASTEST:
        results.sort(
            key=lambda route: (
                route.total_journey_minutes if route.total_journey_minutes is not None else (route.travel_time.expected_minutes + route.waiting_minutes),
                route.fare_bdt,
            )
        )
    elif request.preference == Preference.SHORTEST:
        results.sort(key=lambda route: (route.distance_km, route.total_journey_minutes if route.total_journey_minutes is not None else route.travel_time.expected_minutes))
    else:
        results.sort(
            key=lambda route: (
                route.total_journey_minutes if route.total_journey_minutes is not None else (route.travel_time.expected_minutes + route.waiting_minutes),
                route.fare_bdt,
            )
        )

    from src.disruptions.checker import check_and_attach_disruptions
    results = check_and_attach_disruptions(results, session)

    has_direct_train = bool(train)
    direct_train_msg = (
        None
        if has_direct_train
        else f"No direct train available on this route ({origin} to {destination})."
    )
    return RouteSearchResponse(
        routes=results,
        comparison=_comparison(results),
        direct_train_available=has_direct_train,
        direct_train_message=direct_train_msg,
    )
