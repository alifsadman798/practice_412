from src.database.models import LocalEdge
from src.shared.constants import LOCAL_FARE_BDT, LOCAL_SPEED_KMH
from src.shared.models import Leg, Mode


def create_local_leg(edge: LocalEdge, from_location: str, to_location: str) -> Leg:
    travel_minutes = round(edge.distance_km / LOCAL_SPEED_KMH * 60)
    return Leg(
        mode=Mode.LOCAL,
        origin=from_location,
        destination=to_location,
        service="Local transport (estimated)",
        distance_km=edge.distance_km,
        fare_bdt=LOCAL_FARE_BDT,
        travel_minutes=travel_minutes,
        waiting_minutes=0,
        path=[from_location, to_location],
    )
