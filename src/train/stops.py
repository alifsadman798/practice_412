from datetime import time
from src.database.models import TrainService, TrainStop


def stop_clock(stop: TrainStop, is_origin: bool) -> time | None:
    return stop.departure if is_origin else stop.arrival


def day_offset(stop: TrainStop, service: TrainService, is_origin: bool) -> int:
    if is_origin and stop.district_name == service.from_district:
        return 0
    if not is_origin and stop.district_name == service.to_district:
        return service.day_offset
    return stop.day_offset
