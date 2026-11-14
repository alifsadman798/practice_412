from datetime import date, timedelta

from src.shared.constants import BANGLADESH_64_DISTRICTS


def test_64_districts_list(client):
    res = client.get("/api/districts")
    assert res.status_code == 200
    districts = res.json()
    assert len(districts) == 64
    assert districts == BANGLADESH_64_DISTRICTS
    assert "Dhaka" in districts
    assert "Chattogram" in districts
    assert "Bandarban" in districts
    assert "Barishal" in districts


def test_train_route_includes_stoppages_and_halts(client):
    travel_date = (date.today() + timedelta(days=1)).isoformat()
    res = client.post(
        "/api/search",
        json={
            "origin": "Dhaka",
            "destination": "Chattogram",
            "travel_date": travel_date,
            "departure_time": "06:00",
            "preference": "fastest",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["direct_train_available"] is True
    assert data["direct_train_message"] is None

    train_routes = [r for r in data["routes"] if r["kind"] == "train"]
    assert len(train_routes) > 0
    train_route = train_routes[0]
    train_leg = next(leg for leg in train_route["legs"] if leg["mode"] == "train")
    
    assert len(train_leg["stops"]) > 0
    first_stop = train_leg["stops"][0]
    last_stop = train_leg["stops"][-1]
    assert first_stop["station"] == "Dhaka"
    assert "Chattogram" in last_stop["station"] or last_stop["district_name"] == "Chattogram"
    
    # Check halt minutes calculation
    for stop in train_leg["stops"]:
        assert "halt_minutes" in stop
        assert stop["halt_minutes"] >= 0


def test_no_direct_train_available_indicator(client):
    # Dhaka to Bandarban: no railway station in Bandarban
    travel_date = (date.today() + timedelta(days=1)).isoformat()
    res = client.post(
        "/api/search",
        json={
            "origin": "Dhaka",
            "destination": "Bandarban",
            "travel_date": travel_date,
            "departure_time": "06:00",
            "preference": "fastest",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["direct_train_available"] is False
    assert "No direct train available" in data["direct_train_message"]
    assert "Dhaka" in data["direct_train_message"] and "Bandarban" in data["direct_train_message"]

    # Direct bus or multimodal should still be provided
    kinds = {r["kind"] for r in data["routes"]}
    assert "multimodal" in kinds or "bus" in kinds


def test_multimodal_destination_without_railway(client):
    # Dhaka to Bandarban: train to Chattogram, then bus/local to Bandarban
    travel_date = (date.today() + timedelta(days=1)).isoformat()
    res = client.post(
        "/api/search",
        json={
            "origin": "Dhaka",
            "destination": "Bandarban",
            "travel_date": travel_date,
            "departure_time": "06:00",
            "preference": "cheapest",
        },
    )
    assert res.status_code == 200
    data = res.json()
    mm_routes = [r for r in data["routes"] if r["kind"] == "multimodal"]
    assert len(mm_routes) == 1
    mm = mm_routes[0]
    modes = [leg["mode"] for leg in mm["legs"]]
    assert "train" in modes


def test_multimodal_origin_without_railway(client):
    # Barishal to Dhaka: local/bus from Barishal to Madaripur, then train to Dhaka
    # Pick next operating day (Madhumati Express is off on Saturday)
    target_date = date.today() + timedelta(days=1)
    if target_date.weekday() == 5:
        target_date += timedelta(days=1)
    travel_date = target_date.isoformat()
    res = client.post(
        "/api/search",
        json={
            "origin": "Barishal",
            "destination": "Dhaka",
            "travel_date": travel_date,
            "departure_time": "06:00",
            "preference": "cheapest",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["direct_train_available"] is False
    mm_routes = [r for r in data["routes"] if r["kind"] == "multimodal"]
    assert len(mm_routes) == 1
    mm = mm_routes[0]
    modes = [leg["mode"] for leg in mm["legs"]]
    assert "train" in modes
    assert modes[0] in ("bus", "local")


def test_train_timetable_stoppage_details_times_populated(client):
    res = client.get("/api/timetables/train?origin=Dhaka&destination=Chattogram")
    assert res.status_code == 200
    trains = res.json()
    assert len(trains) > 0

    for train in trains:
        assert "stop_details" in train
        assert len(train["stop_details"]) >= 2
        for halt in train["stop_details"]:
            assert halt["station"]
            assert halt["arrival_time"] is not None and len(halt["arrival_time"]) >= 5
            assert halt["departure_time"] is not None and len(halt["departure_time"]) >= 5
            assert halt["halt_minutes"] >= 0

