from datetime import datetime

from src.shared.constants import TRAIN_TRANSFER_BUFFER_MINUTES
from src.shared.models import Confidence, RouteKind, RouteOption, TimeRange


def combine_segments(
    first: RouteOption,
    second: RouteOption,
    interchange: str,
    first_arrival: datetime,
    second_departure: datetime,
) -> RouteOption:
    transfer_wait = max(
        0, int((second_departure - first_arrival).total_seconds() // 60)
    )
    if first.legs and first.path and not first.legs[0].path:
        first.legs[0].path = first.path
    if second.legs and second.path and not second.legs[0].path:
        second.legs[0].path = second.path
    legs = first.legs + second.legs
    expected = first.travel_time.expected_minutes + second.travel_time.expected_minutes
    minimum = first.travel_time.minimum_minutes + second.travel_time.minimum_minutes
    maximum = first.travel_time.maximum_minutes + second.travel_time.maximum_minutes
    if first.kind == RouteKind.BUS:
        warnings = list(dict.fromkeys(first.warnings + second.warnings))
    else:
        warnings = list(dict.fromkeys(second.warnings + first.warnings))
    warnings.append(
        f"One scheduled transfer at {interchange}; allow at least "
        f"{TRAIN_TRANSFER_BUFFER_MINUTES} minutes."
    )
    if first.path and second.path and first.path[-1].casefold() == second.path[0].casefold():
        route_path = first.path + second.path[1:]
    else:
        route_path = first.path + second.path
    return RouteOption(
        kind=RouteKind.MULTIMODAL,
        path=route_path,
        legs=legs,
        distance_km=round(first.distance_km + second.distance_km, 2),
        fare_bdt=first.fare_bdt + second.fare_bdt,
        travel_time=TimeRange(
            minimum_minutes=minimum + transfer_wait,
            expected_minutes=expected + transfer_wait,
            maximum_minutes=maximum + transfer_wait,
        ),
        waiting_minutes=first.waiting_minutes + transfer_wait,
        transfers=1,
        confidence=Confidence.MEDIUM,
        warnings=warnings,
    )
