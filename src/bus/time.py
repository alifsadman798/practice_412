from datetime import time

from src.shared.constants import BUS_BASE_SPEED_KMH, MAJOR_CITIES, TRAFFIC_FACTORS


def traffic_factor(
    departure: time, factors: dict[str, float] = TRAFFIC_FACTORS
) -> float:
    minutes = departure.hour * 60 + departure.minute
    for period, factor in factors.items():
        start, end = period.split("-")
        start_minutes = int(start[:2]) * 60 + int(start[3:])
        end_minutes = int(end[:2]) * 60 + int(end[3:])
        if (start_minutes < end_minutes and start_minutes <= minutes < end_minutes) or (
            start_minutes > end_minutes
            and (minutes >= start_minutes or minutes < end_minutes)
        ):
            return factor
    raise ValueError("Traffic factors must cover every minute of the day")


def estimated_bus_minutes(
    distance_km: float,
    path: list[str],
    departure: time,
    major_cities: set[str] | frozenset[str] = MAJOR_CITIES,
    traffic_factors: dict[str, float] = TRAFFIC_FACTORS,
) -> int:
    """Manual Traffic-Time Estimation (Section 9):
    Base Time = distance_km / 45 * 60
    Adjusted Time = Base Time / (traffic_factor * city_factor)
    """
    configured_cities = {value.casefold() for value in major_cities}
    major_city_count = sum(
        city.casefold() in configured_cities
        for city in set(path)
    )
    if major_city_count == 0:
        city_factor = 1.0
    elif major_city_count == 1:
        city_factor = 0.9
    elif major_city_count == 2:
        city_factor = 0.8
    else:
        city_factor = 0.7

    base_minutes = distance_km / BUS_BASE_SPEED_KMH * 60
    return max(
        0,
        round(base_minutes / (traffic_factor(departure, traffic_factors) * city_factor)),
    )
