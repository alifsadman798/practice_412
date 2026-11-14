from datetime import datetime, timedelta

from src.database.models import BusSchedule


def next_bus_departure(
    schedules: list[BusSchedule], requested: datetime
) -> tuple[BusSchedule, datetime, datetime, int] | None:
    candidates: list[tuple[datetime, datetime, BusSchedule, int]] = []
    same_day_candidates: list[tuple[datetime, datetime, BusSchedule, int]] = []
    for service in schedules:
        departure = datetime.combine(requested.date(), service.departure)
        if departure >= requested:
            arrival = datetime.combine(departure.date(), service.arrival)
            if arrival < departure:
                arrival += timedelta(days=1)
            same_day_candidates.append(
                (departure, arrival, service, int((departure - requested).total_seconds() // 60))
            )
        else:
            dep_tomorrow = departure + timedelta(days=1)
            arr_tomorrow = datetime.combine(dep_tomorrow.date(), service.arrival)
            if arr_tomorrow < dep_tomorrow:
                arr_tomorrow += timedelta(days=1)
            candidates.append(
                (dep_tomorrow, arr_tomorrow, service, int((dep_tomorrow - requested).total_seconds() // 60))
            )
    pool = same_day_candidates if same_day_candidates else candidates
    if not pool:
        return None
    departure, arrival, service, waiting = min(
        pool, key=lambda item: (item[0], item[2].transport_name.casefold())
    )
    return service, departure, arrival, waiting
