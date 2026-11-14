from decimal import Decimal, ROUND_HALF_UP

VIP_TRAIN_SURCHARGE_BDT = 60
VIP_MAX_INTERMEDIATE_STOPS = 2


def train_fare(distance_km: float, intermediate_stop_count: int) -> int:
    """Calculate train fare:

    Formula:
      Train Fare = 40 + 1.5 * distance_km + (60 if intermediate_stops <= 2 else 0)
    where:
      intermediate_stop_count: number of intermediate stoppages between initial start and last destination
    """
    if distance_km < 0:
        raise ValueError("Train distance cannot be negative")
    if intermediate_stop_count < 0:
        raise ValueError("Intermediate stop count cannot be negative")

    dist = Decimal(str(distance_km))
    amount = Decimal("40") + (Decimal("1.5") * dist)
    if intermediate_stop_count <= VIP_MAX_INTERMEDIATE_STOPS:
        amount += Decimal(VIP_TRAIN_SURCHARGE_BDT)
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
