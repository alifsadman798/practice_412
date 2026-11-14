from datetime import time
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models import (
    BusSchedule,
    District,
    DistrictEdge,
    LocalEdge,
    RoutingConfig,
    TrainService,
    TrainStop,
)
from src.data.graph import shortest_path
from src.bus.fare import bus_fare
from src.bus.time import estimated_bus_minutes, traffic_factor
from src.train.fare import train_fare
from src.shared.constants import TRAFFIC_FACTORS


def test_csv_import_has_verified_dataset_counts(test_engine):
    with Session(test_engine) as session:
        assert session.scalar(select(func.count()).select_from(District)) >= 64
        assert session.scalar(select(func.count()).select_from(DistrictEdge)) == 121
        assert session.scalar(select(func.count()).select_from(LocalEdge)) >= 160
        assert session.scalar(select(func.count()).select_from(BusSchedule)) == 10134
        assert session.scalar(select(func.count()).select_from(TrainService)) == 115
        assert session.scalar(select(func.count()).select_from(TrainStop)) == 1539
        assert session.scalar(select(func.count()).select_from(RoutingConfig)) == 3


def test_seed_refuses_to_overwrite_admin_data_without_force(test_engine):
    from src.database.seed import seed_database

    with Session(test_engine) as session, pytest.raises(
        RuntimeError, match="refusing to overwrite"
    ):
        seed_database(session, Path("data"), force=False)


def test_undirected_shortest_path_is_reverse_consistent():
    edges = [
        DistrictEdge(from_district="A", to_district="B", distance_km=4),
        DistrictEdge(from_district="B", to_district="D", distance_km=5),
        DistrictEdge(from_district="A", to_district="C", distance_km=4),
        DistrictEdge(from_district="C", to_district="D", distance_km=5),
    ]
    forward = shortest_path(edges, "A", "D")
    reverse = shortest_path(edges, "D", "A")
    assert forward == (["A", "B", "D"], 9)
    assert reverse == (["D", "B", "A"], 9)


def test_bus_fare_counts_each_core_city_once_and_rounds_half_up():
    assert bus_fare(10.25, ["Dhaka", "Dhaka", "Gazipur"]) == 121
    assert bus_fare(10.25, ["Gazipur", "Dhaka", "Dhaka"]) == 121


@pytest.mark.parametrize(
    ("clock", "expected"),
    [
        (time(5, 59), 1.2),
        (time(6, 0), 1.0),
        (time(8, 0), 0.7),
        (time(10, 0), 1.0),
        (time(17, 0), 0.7),
        (time(20, 0), 1.0),
        (time(22, 0), 1.2),
        (time(23, 59), 1.2),
    ],
)
def test_traffic_factor_boundaries(clock, expected):
    assert traffic_factor(clock) == expected


def test_traffic_factors_cover_every_minute():
    for minute in range(24 * 60):
        assert traffic_factor(time(minute // 60, minute % 60)) > 0
    with pytest.raises(ValueError, match="cover every minute"):
        traffic_factor(time(3, 0), {"06:00-08:00": 1.0})


def test_bus_time_uses_major_city_count_and_configurable_factors():
    base = estimated_bus_minutes(45, ["Gazipur", "Bhairab"], time(6, 0))
    peak = estimated_bus_minutes(45, ["Gazipur", "Bhairab"], time(8, 0))
    assert base == 60
    assert peak > base
    assert TRAFFIC_FACTORS["22:00-06:00"] == 1.2


@pytest.mark.parametrize(
    ("intermediate_stops", "expected_fare"),
    [(0, 250), (1, 250), (2, 250), (3, 190)],
)
def test_train_fare_applies_vip_surcharge_by_intermediate_stops(
    intermediate_stops, expected_fare
):
    assert train_fare(100, intermediate_stops) == expected_fare


@pytest.mark.parametrize(
    ("distance_km", "intermediate_stops"),
    [(-1, 0), (100, -1)],
)
def test_train_fare_rejects_negative_inputs(distance_km, intermediate_stops):
    with pytest.raises(ValueError):
        train_fare(distance_km, intermediate_stops)
