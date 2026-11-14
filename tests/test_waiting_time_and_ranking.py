from fastapi.testclient import TestClient
from src.api.main import app


def _to_mins(t: str) -> int:
    parts = t.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def test_initial_waiting_time_and_metadata(client: TestClient):
    """Verify that initial waiting time at origin and first service metadata are accurately calculated."""
    res = client.post(
        "/api/search",
        json={"origin": "Dhaka", "destination": "Sylhet", "departure_time": "06:00"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["routes"]) > 0

    for route in data["routes"]:
        assert "initial_waiting_minutes" in route
        assert route["initial_waiting_minutes"] is not None
        assert route["initial_waiting_minutes"] >= 0

        assert "next_departure_time" in route
        assert "next_departure_service" in route
        assert "next_departure_mode" in route
        assert "next_departure_location" in route
        assert "in_journey_minutes" in route
        assert "total_journey_minutes" in route

        # Verify initial wait + in-journey equals total journey minutes without double counting
        expected_total = route["in_journey_minutes"] + route["initial_waiting_minutes"]
        assert route["total_journey_minutes"] == expected_total

        # If next departure time is available, verify initial wait matches diff from 06:00
        if route["next_departure_time"]:
            dep_m = _to_mins(route["next_departure_time"])
            req_m = _to_mins("06:00")
            expected_wait = dep_m - req_m if dep_m >= req_m else (dep_m + 1440 - req_m)
            # The first leg waiting_minutes matches the computed initial_waiting_minutes
            assert route["initial_waiting_minutes"] == expected_wait


def test_transfer_station_waiting_time_and_ready_time(client: TestClient):
    """Verify that multimodal transfers separately report local transit time and station wait time."""
    res = client.post(
        "/api/search",
        json={"origin": "Dhaka", "destination": "Sylhet", "departure_time": "06:00"},
    )
    assert res.status_code == 200
    data = res.json()

    mm_routes = [r for r in data["routes"] if r["kind"] == "multimodal"]
    assert len(mm_routes) >= 1
    route = mm_routes[0]

    transfer_leg = route["legs"][0]
    assert transfer_leg["transfer_to_next"] is not None
    tr = transfer_leg["transfer_to_next"]

    assert "ready_to_board_time" in tr
    assert "station_waiting_minutes" in tr
    assert "travel_minutes" in tr
    assert "prev_arrival_time" in tr
    assert "next_departure_time" in tr

    # Verify that local transit time and station waiting time are distinct values
    assert tr["travel_minutes"] > 0
    if tr["prev_arrival_time"] and tr["ready_to_board_time"]:
        arr_m = _to_mins(tr["prev_arrival_time"])
        ready_m = _to_mins(tr["ready_to_board_time"])
        transit_m = tr["travel_minutes"]
        expected_ready = (arr_m + transit_m) % 1440
        assert ready_m == expected_ready


def test_fastest_ranking_uses_total_journey_time(client: TestClient):
    """Verify that ranking under FASTEST preference optimizes total elapsed journey time."""
    res = client.post(
        "/api/search",
        json={
            "origin": "Dhaka",
            "destination": "Sylhet",
            "departure_time": "08:00",
            "preference": "fastest",
        },
    )
    assert res.status_code == 200
    data = res.json()
    routes = data["routes"]
    assert len(routes) >= 2

    for i in range(len(routes) - 1):
        cur = routes[i]["total_journey_minutes"]
        nxt = routes[i + 1]["total_journey_minutes"]
        assert cur <= nxt, f"Route at index {i} ({cur} mins) should be <= route at index {i+1} ({nxt} mins)"
