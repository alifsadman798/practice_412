from datetime import date, timedelta
from unittest.mock import patch

from sqlalchemy.exc import OperationalError

from src.database.connection import get_db
from src.api.main import app


def test_public_pages_and_health(client):
    for route in ["/", "/journey", "/plan", "/timetables"]:
        assert client.get(route).status_code == 200
    assert client.get("/admin").status_code == 200
    assert client.get("/alerts").status_code == 404
    assert client.get("/travel-alerts").status_code == 404
    assert client.get("/api/alerts").status_code == 404
    assert client.get("/api/reports").status_code == 404
    assert client.get("/api/health").json() == {"status": "ok", "database": "ok"}
    assert len(client.get("/api/districts").json()) >= 64
    locations = client.get("/api/locations").json()
    assert any(location["name"] == "Bhairab" for location in locations)
    assert any(location["name"] == "Dhaka Airport" for location in locations)


def test_database_failure_is_reported_without_csv_fallback(client):
    def unavailable_database():
        raise OperationalError("SELECT 1", {}, ConnectionError("database down"))
        yield

    app.dependency_overrides[get_db] = unavailable_database
    try:
        response = client.get("/api/districts")
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert response.status_code == 503
    assert "Database unavailable" in response.json()["detail"]


def test_route_search_returns_database_backed_options(client):
    response = client.post(
        "/api/search",
        json={
            "origin": "Dhaka",
            "destination": "Cumilla",
            "travel_date": (date.today() + timedelta(days=1)).isoformat(),
            "departure_time": "06:00",
            "preference": "balanced",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["routes"]
    assert {route["kind"] for route in body["routes"]} & {"bus", "train", "multimodal"}
    assert all(route["fare_bdt"] >= 0 for route in body["routes"])


def test_route_validation_distinguishes_invalid_and_unsupported(client):
    same_location = client.post(
        "/api/search", json={"origin": "Dhaka", "destination": "dhaka"}
    )
    unsupported = client.post(
        "/api/search", json={"origin": "Atlantis", "destination": "Dhaka"}
    )
    past_date = client.post(
        "/api/search",
        json={
            "origin": "Dhaka",
            "destination": "Cumilla",
            "travel_date": "2020-01-01",
            "departure_time": "12:00",
        },
    )
    assert same_location.status_code == 422
    assert unsupported.status_code == 422
    assert past_date.status_code == 422


def test_timetable_bus_search(client):
    response = client.get("/api/timetables/bus?origin=Dhaka&destination=Gazipur")
    assert response.status_code == 200
    items = response.json()
    assert len(items) > 0
    assert any("Gazipur" in item["destination"] for item in items)
    assert all(item["fare_bdt"] == 90 for item in items)


def test_bus_fare_from_csv_in_routing_and_timetables(client):
    # Timetable returns fare from CSV
    tb_resp = client.get("/api/timetables/bus?origin=Bandarban&destination=Brahmanbaria")
    assert tb_resp.status_code == 200
    tb_items = tb_resp.json()
    assert len(tb_items) > 0
    assert all(item["fare_bdt"] == 650 for item in tb_items)

    # Route search returns bus route with exact fare from CSV
    travel_date = (date.today() + timedelta(days=1)).isoformat()
    search_resp = client.post(
        "/api/search",
        json={
            "origin": "Dhaka",
            "destination": "Chattogram",
            "travel_date": travel_date,
            "departure_time": "07:00",
            "preference": "fastest",
        },
    )
    assert search_resp.status_code == 200
    routes = search_resp.json()["routes"]
    bus_route = next(r for r in routes if r["kind"] == "bus")
    assert bus_route["fare_bdt"] == 690
    assert bus_route["legs"][0]["fare_bdt"] == 690


def test_timetable_train_search(client):
    response = client.get("/api/timetables/train?train_no=701")
    assert response.status_code == 200
    items = response.json()
    assert len(items) > 0
    assert items[0]["train_no"] == "701"
    assert "Suborna" in items[0]["train_name"]


def test_admin_auth_required(client):
    unauth = client.get("/api/admin/districts")
    assert unauth.status_code == 401

    auth = client.get(
        "/api/admin/districts",
        headers={"Authorization": "Basic YWRtaW46MTIzNDU2Nzg="},
    )
    assert auth.status_code == 200
    assert len(auth.json()) >= 64
