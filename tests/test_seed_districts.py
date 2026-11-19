import pytest
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.database.models import District, TrainService, TrainStop, Location
from src.database.seed import build_station_district_resolver, seed_database
from src.data.loader import read_csv
from src.data.normalize import normalize_name
from src.shared.constants import BANGLADESH_64_DISTRICTS


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
def official_districts():
    district_edges_data = read_csv(DATA_DIR, "64_districts.csv")
    districts = set()
    for row in district_edges_data:
        districts.add(normalize_name(row["From"].strip()))
        districts.add(normalize_name(row["To"].strip()))
    return districts


@pytest.fixture(scope="module")
def station_resolver(official_districts):
    local_edges_data = read_csv(DATA_DIR, "local_distance.csv")
    district_edges_data = read_csv(DATA_DIR, "64_districts.csv")
    return build_station_district_resolver(
        official_districts, local_edges_data, district_edges_data
    )


def test_official_district_count(client):
    """Test 1: Official District Count in DB is exactly 64."""
    res = client.get("/api/admin/districts", auth=("admin", "12345678"))
    assert res.status_code == 200
    districts = res.json()
    assert len(districts) == 64


def test_official_district_names(client):
    """Test 2: District Names match the 64 official Bangladesh districts."""
    res = client.get("/api/admin/districts", auth=("admin", "12345678"))
    assert res.status_code == 200
    districts = res.json()
    assert districts == sorted(BANGLADESH_64_DISTRICTS)


def test_automatic_district_matching(station_resolver):
    """Test 3: Automatic District Matching for Priority 1 and Priority 2 stations."""
    expected_mappings = {
        "Dhaka": "Dhaka",
        "Dhaka Airport": "Dhaka",
        "Chattogram": "Chattogram",
        "Rajshahi": "Rajshahi",
        "Benapole": "Jashore",
        "Burimari": "Lalmonirhat",
        "Chilahati": "Nilphamari",
        "Dhalarchar": "Pabna",
        "Gobra": "Gopalganj",
        "Santahar": "Bogura",
        "Sirajganj Bazar": "Sirajganj",
    }
    for station, expected_district in expected_mappings.items():
        assert station_resolver(station) == expected_district


def test_ambiguous_station_names(station_resolver):
    """Test 4: Ambiguous station names without context raise ValueError, with context resolve reliably."""
    # Without context, standalone call must raise ValueError
    with pytest.raises(ValueError) as excinfo_noyapara:
        station_resolver("Noyapara")
    assert "Ambiguous railway station 'Noyapara'" in str(excinfo_noyapara.value)

    with pytest.raises(ValueError) as excinfo_lohagara:
        station_resolver("Lohagara")
    assert "Ambiguous railway station 'Lohagara'" in str(excinfo_lohagara.value)

    # With train context for Train 715 (Kapotaksha Express: Khulna -> Jashore corridor)
    mock_train_715_stops = [
        {"Train_No": "715", "Stop_Order": "1", "Station": "Khulna", "District": ""},
        {"Train_No": "715", "Stop_Order": "2", "Station": "Noyapara", "District": ""},
        {"Train_No": "715", "Stop_Order": "3", "Station": "Jashore", "District": ""},
    ]
    resolved_noyapara = station_resolver(
        "Noyapara",
        train_no="715",
        stop_order=2,
        stop_idx=1,
        train_stops=mock_train_715_stops,
    )
    assert resolved_noyapara == "Jashore"

    # With train context for Train 825 (Jahanabad Express: Narail corridor)
    mock_train_825_stops = [
        {"Train_No": "825", "Stop_Order": "4", "Station": "Narail", "District": ""},
        {"Train_No": "825", "Stop_Order": "5", "Station": "Lohagara", "District": ""},
        {"Train_No": "825", "Stop_Order": "6", "Station": "Kashiani", "District": ""},
    ]
    resolved_lohagara = station_resolver(
        "Lohagara",
        train_no="825",
        stop_order=5,
        stop_idx=1,
        train_stops=mock_train_825_stops,
    )
    assert resolved_lohagara == "Narail"


def test_unknown_station_raises_error(station_resolver):
    """Test 5: Unknown Station must raise a clear ValueError and NEVER default to Dhaka."""
    with pytest.raises(ValueError) as excinfo:
        station_resolver("Atlantis Central Station")
    assert "Cannot resolve railway station 'Atlantis Central Station'" in str(excinfo.value)
    # Ensure Dhaka is not returned
    assert "Dhaka" not in str(excinfo.value) or "missing or unknown" in str(excinfo.value)


def test_train_services_all_reference_official_districts(test_engine):
    """Test 6: Every TrainService.from_district and to_district references an official district."""
    with Session(test_engine) as session:
        services = session.scalars(select(TrainService)).all()
        assert len(services) > 0
        official_set = set(BANGLADESH_64_DISTRICTS)
        for srv in services:
            assert srv.from_district in official_set, f"Invalid from_district: {srv.from_district}"
            assert srv.to_district in official_set, f"Invalid to_district: {srv.to_district}"


def test_train_stops_district_assignment(test_engine):
    """Test 7: Every TrainStop.district_name references an official district and stations remain distinct."""
    with Session(test_engine) as session:
        stops = session.scalars(select(TrainStop)).all()
        assert len(stops) > 0
        official_set = set(BANGLADESH_64_DISTRICTS)
        for stop in stops:
            assert stop.district_name in official_set, f"Invalid district_name: {stop.district_name}"
            assert stop.station != "", "Station name must not be empty"

        # Check that station records in Location have kind='station' and not in District table
        district_count = session.scalar(select(func.count()).select_from(District))
        assert district_count == 64
        terminal_stations = ["Benapole", "Burimari", "Chilahati", "Dhalarchar", "Gobra", "Santahar", "Sirajganj Bazar"]
        for st in terminal_stations:
            # Must NOT be in districts table
            assert session.scalar(select(District).where(District.name == st)) is None
            # Must be in locations table with kind='station'
            loc = session.scalar(select(Location).where(Location.name == st))
            assert loc is not None
            assert loc.kind == "station"
