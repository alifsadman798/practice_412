from datetime import date, datetime, time as datetime_time
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.shared.constants import BANGLADESH_TIME
from src.shared.enums import Confidence, Mode, Preference, RouteKind


class TimeRange(BaseModel):
    minimum_minutes: int = Field(ge=0)
    expected_minutes: int = Field(ge=0)
    maximum_minutes: int = Field(ge=0)

    @model_validator(mode="after")
    def ordered_range(self):
        if not (
            self.minimum_minutes
            <= self.expected_minutes
            <= self.maximum_minutes
        ):
            raise ValueError("Travel-time range must be in ascending order")
        return self


class TrainHalt(BaseModel):
    station: str
    district_name: str
    arrival: datetime_time | None = Field(default=None, alias="arrival_time")
    departure: datetime_time | None = Field(default=None, alias="departure_time")
    halt_minutes: int = 0
    stop_order: int

    model_config = ConfigDict(populate_by_name=True)


class Leg(BaseModel):
    mode: Mode
    origin: str
    destination: str
    service: str
    departure: datetime_time | None = Field(default=None, alias="departure_time")
    arrival: datetime_time | None = Field(default=None, alias="arrival_time")
    distance_km: float = Field(ge=0)
    fare_bdt: int = Field(ge=0)
    travel_minutes: int = Field(ge=0)
    waiting_minutes: int = Field(ge=0)
    stops: list[TrainHalt] = Field(default_factory=list)
    path: list[str] = Field(default_factory=list)
    transfer_to_next: dict | None = None
    is_affected: bool = False
    disruption_alerts: list[dict] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class RouteOption(BaseModel):
    kind: RouteKind
    path: list[str]
    legs: list[Leg]
    distance_km: float = Field(ge=0)
    fare_bdt: int = Field(ge=0)
    travel_time: TimeRange
    waiting_minutes: int = Field(ge=0)
    transfers: int = Field(ge=0)
    confidence: Confidence
    warnings: list[str] = Field(default_factory=list)
    is_affected: bool = False
    disruption_alerts: list[dict] = Field(default_factory=list)
    initial_waiting_minutes: int | None = None
    next_departure_time: str | None = None
    next_departure_service: str | None = None
    next_departure_mode: str | None = None
    next_departure_location: str | None = None
    in_journey_minutes: int | None = None
    total_journey_minutes: int | None = None
    recommendation_reason: str | None = None
    ranking_score: float | None = None


Route = RouteOption


class RouteSearchRequest(BaseModel):
    origin: str = Field(min_length=1, max_length=120)
    destination: str = Field(min_length=1, max_length=120)
    travel_date: date = Field(
        default_factory=lambda: datetime.now(BANGLADESH_TIME).date()
    )
    departure_time: datetime_time = Field(
        default_factory=lambda: datetime.now(BANGLADESH_TIME)
        .time()
        .replace(second=0, microsecond=0)
    )
    preference: Preference = Preference.BALANCED

    @field_validator("origin", "destination")
    @classmethod
    def trim_location(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Location cannot be blank")
        return value

    @model_validator(mode="after")
    def distinct_locations(self):
        if self.origin.casefold() == self.destination.casefold():
            raise ValueError("Origin and destination must be different")
        now = datetime.now(BANGLADESH_TIME)
        if self.travel_date < now.date():
            raise ValueError("Travel date cannot be in the past")
        return self


SearchRequest = RouteSearchRequest


class Comparison(BaseModel):
    cheapest: RouteOption | None = None
    fastest: RouteOption | None = None
    shortest: RouteOption | None = None
    note: str


class RouteSearchResponse(BaseModel):
    routes: list[RouteOption]
    comparison: Comparison
    direct_train_available: bool = True
    direct_train_message: str | None = None


SearchResponse = RouteSearchResponse


class BusTimetableItem(BaseModel):
    travel_date: date
    route_id: str
    origin: str
    destination: str
    transport_name: str
    departure: datetime_time
    arrival: datetime_time
    fare_bdt: int = 0
    fare: int = 0
    scheduled_only: bool = True


class TrainTimetableItem(BaseModel):
    travel_date: date
    train_no: str
    train_name: str
    origin: str
    destination: str
    departure: datetime_time
    arrival: datetime_time
    off_day: str
    day_offset: int
    operating_on_date: bool
    stops: list[str] = Field(default_factory=list)
    stop_details: list[TrainHalt] = Field(default_factory=list)
    scheduled_only: bool = True


class LocalTransportItem(BaseModel):
    id: int
    from_location: str
    to_location: str
    parent_district: str
    distance_km: float
    vehicle_types: list[str] = Field(
        default_factory=lambda: ["CNG Auto-Rickshaw", "Shared Easy Bike", "Feeder Shuttle / Minibus"]
    )
    est_duration_minutes: int
    est_fare_min_bdt: int
    est_fare_max_bdt: int
    frequency: str = "Continuous local dispatch (every 5-15 mins)"

