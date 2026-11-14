from decimal import Decimal, ROUND_HALF_UP

from src.shared.constants import CORE_CITIES


def bus_fare(
    distance_km: float,
    path: list[str],
    core_cities: set[str] | frozenset[str] = CORE_CITIES,
) -> int:
    """Bus Fare Formula (Section 7):
    Bus Fare = 50 + 50 * core_city_count + 2 * total_distance_km
    where core_city_count is the unique qualifying core-city districts visited.
    """
    configured = {value.casefold() for value in core_cities}
    core_city_count = sum(city.casefold() in configured for city in set(path))
    amount = Decimal("50") + Decimal("50") * core_city_count + Decimal("2") * Decimal(
        str(distance_km)
    )
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
