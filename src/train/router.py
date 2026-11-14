from collections import defaultdict
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import TrainService, TrainStop
from src.train.fare import (
    VIP_MAX_INTERMEDIATE_STOPS,
    VIP_TRAIN_SURCHARGE_BDT,
    train_fare,
)
from src.train.schedule import is_off_day
from src.train.stops import day_offset as _day_offset, stop_clock as _stop_clock
from src.shared.models import (
    Confidence,
    Leg,
    Mode,
    RouteKind,
    RouteOption,
    TimeRange,
    TrainHalt,
)

_is_off_day = is_off_day


def load_train_network(
    session: Session,
) -> tuple[list[TrainService], dict[str, list[TrainStop]]]:
    services = list(
        session.scalars(select(TrainService).order_by(TrainService.train_no))
    )
    stops_by_train: dict[str, list[TrainStop]] = defaultdict(list)
    for stop in session.scalars(
        select(TrainStop).order_by(TrainStop.train_no, TrainStop.stop_order)
    ):
        stops_by_train[stop.train_no].append(stop)
    return services, dict(stops_by_train)


def train_trip(
    session: Session,
    origin: str,
    destination: str,
    requested: datetime,
    origin_station: str | None = None,
    destination_station: str | None = None,
    services: list[TrainService] | None = None,
    stops_by_train: dict[str, list[TrainStop]] | None = None,
) -> tuple[RouteOption, datetime, datetime] | None:
    if services is None or stops_by_train is None:
        services, stops_by_train = load_train_network(session)
    possible: list[tuple[int, datetime, str, RouteOption, datetime, datetime]] = []
    for service in services:
        stops = stops_by_train.get(service.train_no, [])
        origin_indices = [
            i
            for i, stop in enumerate(stops)
            if (
                stop.district_name.casefold() == origin.casefold()
                or (origin_station and stop.station.casefold() == origin_station.casefold())
                or stop.station.casefold() == origin.casefold()
            )
            and (
                origin_station is None
                or stop.station.casefold() == origin_station.casefold()
            )
        ]
        if origin_station is None:
            exact_origin = [i for i in origin_indices if stops[i].station.casefold() == origin.casefold()]
            if exact_origin:
                origin_indices = exact_origin

        destination_indices = [
            i
            for i, stop in enumerate(stops)
            if (
                stop.district_name.casefold() == destination.casefold()
                or (destination_station and stop.station.casefold() == destination_station.casefold())
                or stop.station.casefold() == destination.casefold()
            )
            and (
                destination_station is None
                or stop.station.casefold() == destination_station.casefold()
            )
        ]
        if destination_station is None:
            exact_dest = [i for i in destination_indices if stops[i].station.casefold() == destination.casefold()]
            if exact_dest:
                destination_indices = exact_dest

        matching: list[tuple[int, int]] = [
            (left, right)
            for left in origin_indices
            for right in destination_indices
            if left < right
        ]
        if not matching:
            continue
        for start_index, end_index in matching:
            start_stop, end_stop = stops[start_index], stops[end_index]
            departure_clock = _stop_clock(start_stop, True)
            arrival_clock = _stop_clock(end_stop, False)
            if departure_clock is None or arrival_clock is None:
                continue
            start_offset = _day_offset(start_stop, service, True)
            end_offset = _day_offset(end_stop, service, False)
            service_date = requested.date()
            for _ in range(8):
                if not _is_off_day(service.off_day, service_date):
                    break
                service_date += timedelta(days=1)
            departure = datetime.combine(service_date, departure_clock) + timedelta(days=start_offset)
            while departure < requested:
                service_date += timedelta(days=1)
                while _is_off_day(service.off_day, service_date):
                    service_date += timedelta(days=1)
                departure = datetime.combine(service_date, departure_clock) + timedelta(days=start_offset)
            arrival = datetime.combine(service_date, arrival_clock) + timedelta(days=end_offset)
            if arrival < departure:
                arrival += timedelta(days=1)
            waiting = int((departure - requested).total_seconds() // 60)
            travel = int((arrival - departure).total_seconds() // 60)
            distance = max(
                0.0, end_stop.cumulative_km - start_stop.cumulative_km
            )
            if distance == 0:
                continue
            route_stops = stops[start_index : end_index + 1]
            intermediate_stop_count = max(0, len(route_stops) - 2)
            fare = train_fare(distance, intermediate_stop_count)
            path: list[str] = []
            for stop in route_stops:
                st = stop.station.strip()
                dist = (stop.district_name or "").strip()
                label = st if (not dist or st.casefold() == dist.casefold()) else f"{st} ({dist})"
                if not path or path[-1].casefold() != label.casefold():
                    path.append(label)
            warnings = [
                "Train schedules are published timetable information; live delays are not verified."
            ]
            if intermediate_stop_count <= VIP_MAX_INTERMEDIATE_STOPS:
                warnings.append(
                    f"VIP fare: {intermediate_stop_count} intermediate stop(s), "
                    f"including a BDT {VIP_TRAIN_SURCHARGE_BDT} surcharge."
                )
            halt_list: list[TrainHalt] = []
            for s in route_stops:
                arr = s.arrival
                dep = s.departure
                halt_mins = 0
                if arr and dep:
                    arr_total = arr.hour * 60 + arr.minute
                    dep_total = dep.hour * 60 + dep.minute
                    halt_mins = dep_total - arr_total
                    if halt_mins < 0:
                        halt_mins += 24 * 60
                if arr is None and dep is not None:
                    arr = dep
                if dep is None and arr is not None:
                    dep = arr
                halt_list.append(
                    TrainHalt(
                        station=s.station,
                        district_name=s.district_name,
                        arrival_time=arr,
                        departure_time=dep,
                        halt_minutes=halt_mins,
                        stop_order=s.stop_order,
                    )
                )
            option = RouteOption(
                kind=RouteKind.TRAIN,
                path=path,
                legs=[
                    Leg(
                        mode=Mode.TRAIN,
                        origin=origin_station or start_stop.station,
                        destination=destination_station or end_stop.station,
                        service=f"{service.train_name} ({service.train_no})",
                        departure_time=departure_clock,
                        arrival_time=arrival_clock,
                        distance_km=distance,
                        fare_bdt=fare,
                        travel_minutes=travel,
                        waiting_minutes=waiting,
                        stops=halt_list,
                        path=path,
                    )
                ],
                distance_km=distance,
                fare_bdt=fare,
                travel_time=TimeRange(
                    minimum_minutes=max(1, round(travel * 0.95)),
                    expected_minutes=travel,
                    maximum_minutes=round(travel * 1.15),
                ),
                waiting_minutes=waiting,
                transfers=0,
                confidence=Confidence.HIGH,
                warnings=warnings,
            )
            possible.append(
                (waiting, intermediate_stop_count, departure, service.train_no, option, departure, arrival)
            )
    if not possible:
        return None
    _, _, _, _, option, departure, arrival = min(
        possible,
        key=lambda result: (result[0], result[1], result[2], result[3]),
    )
    return option, departure, arrival


def train_timetable(
    session: Session,
    travel_date: date,
    train_no: str | None = None,
    train_name: str | None = None,
    origin: str | None = None,
    destination: str | None = None,
) -> list[dict]:
    query = select(TrainService).order_by(TrainService.train_no)
    if train_no:
        query = query.where(TrainService.train_no.ilike(f"%{train_no.strip()}%"))
    if train_name:
        query = query.where(TrainService.train_name.ilike(f"%{train_name.strip()}%"))
    results = []
    for service in session.scalars(query):
        stops = list(
            session.scalars(
                select(TrainStop)
                .where(TrainStop.train_no == service.train_no)
                .order_by(TrainStop.stop_order)
            )
        )
        from_index = next(
            (
                i
                for i, stop in enumerate(stops)
                if origin
                and (
                    stop.district_name.casefold() == origin.casefold()
                    or stop.station.casefold() == origin.casefold()
                )
            ),
            0,
        )
        if origin:
            exact_from = next((i for i, s in enumerate(stops) if s.station.casefold() == origin.casefold()), None)
            if exact_from is not None:
                from_index = exact_from

        to_index = next(
            (
                i
                for i, stop in enumerate(stops)
                if destination
                and (
                    stop.district_name.casefold() == destination.casefold()
                    or stop.station.casefold() == destination.casefold()
                )
            ),
            len(stops) - 1,
        )
        if destination:
            exact_to = next((i for i, s in enumerate(stops) if s.station.casefold() == destination.casefold()), None)
            if exact_to is not None:
                to_index = exact_to
        if origin and not any(
            s.district_name.casefold() == origin.casefold()
            or s.station.casefold() == origin.casefold()
            for s in stops
        ):
            continue
        if destination and not any(
            s.district_name.casefold() == destination.casefold()
            or s.station.casefold() == destination.casefold()
            for s in stops
        ):
            continue
        if from_index >= to_index:
            continue
        start, end = stops[from_index], stops[to_index]
        departure = start.departure or service.departure
        arrival = end.arrival or service.arrival
        segment_stops = stops[from_index : to_index + 1]
        detailed_halts: list[TrainHalt] = []
        for s in segment_stops:
            arr = s.arrival
            dep = s.departure
            halt_mins = 0
            if arr and dep:
                arr_total = arr.hour * 60 + arr.minute
                dep_total = dep.hour * 60 + dep.minute
                halt_mins = dep_total - arr_total
                if halt_mins < 0:
                    halt_mins += 24 * 60
            if arr is None and dep is not None:
                arr = dep
            if dep is None and arr is not None:
                dep = arr
            detailed_halts.append(
                TrainHalt(
                    station=s.station,
                    district_name=s.district_name,
                    arrival_time=arr,
                    departure_time=dep,
                    halt_minutes=halt_mins,
                    stop_order=s.stop_order,
                )
            )
        results.append(
            {
                "travel_date": travel_date,
                "train_no": service.train_no,
                "train_name": service.train_name,
                "origin": start.station,
                "destination": end.station,
                "departure": departure,
                "arrival": arrival,
                "off_day": service.off_day,
                "day_offset": max(0, end.day_offset - start.day_offset),
                "operating_on_date": not _is_off_day(service.off_day, travel_date),
                "stops": [stop.station for stop in segment_stops],
                "stop_details": detailed_halts,
            }
        )
    return results
