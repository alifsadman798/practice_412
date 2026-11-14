from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.database.models import District, Location
from src.bus.fare import bus_fare
from src.data.graph import shortest_path
from src.database.repositories import DataStore


def test_reverse_route_consistency_fare_and_distance(test_engine):
    with Session(test_engine) as session:
        store = DataStore(session)
        edges = store.get_district_graph()
        fwd_path, fwd_dist = shortest_path(edges, "Dhaka", "Cumilla")
        rev_path, rev_dist = shortest_path(edges, "Cumilla", "Dhaka")

        assert fwd_dist == rev_dist
        assert fwd_path == list(reversed(rev_path))

        fwd_fare = bus_fare(fwd_dist, fwd_path)
        rev_fare = bus_fare(rev_dist, rev_path)
        assert fwd_fare == rev_fare


def test_full_search_with_comparisons(client: TestClient):
    travel_date = (date.today() + timedelta(days=1)).isoformat()
    response = client.post(
        "/api/search",
        json={
            "origin": "Dhaka",
            "destination": "Chattogram",
            "travel_date": travel_date,
            "departure_time": "07:00",
            "preference": "fastest",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "routes" in data
    assert len(data["routes"]) > 0
    assert "comparison" in data
    comp = data["comparison"]
    assert comp["cheapest"] is not None
    assert comp["fastest"] is not None
    assert comp["shortest"] is not None
    assert comp["note"] != ""


def test_admin_crud_workflow(client: TestClient):
    auth_header = {"Authorization": "Basic YWRtaW46MTIzNDU2Nzg="}

    # Verify that location/district mutations are disallowed (managed strictly via CSV)
    disallowed_loc = client.post(
        "/api/admin/locations",
        json={"name": "Test Bazar", "kind": "upazila", "district_name": "Dhaka"},
        headers=auth_header,
    )
    assert disallowed_loc.status_code in {404, 405}

    # Admin CAN manage transport records (Train Service CRUD)
    add_resp = client.post(
        "/api/admin/train-services",
        json={
            "train_no": "9999",
            "train_name": "Test Special Express",
            "from_district": "Dhaka",
            "to_district": "Chattogram",
            "off_day": "None",
            "departure": "08:00:00",
            "arrival": "14:00:00",
            "day_offset": 0,
        },
        headers=auth_header,
    )
    assert add_resp.status_code == 201
    srv_id = add_resp.json()["id"]

    # Verify presence in train services list
    list_resp = client.get("/api/admin/train-services", headers=auth_header)
    assert list_resp.status_code == 200
    assert any(s["train_no"] == "9999" for s in list_resp.json())

    # Update train service
    update_resp = client.put(
        f"/api/admin/train-services/{srv_id}",
        json={
            "train_no": "9999",
            "train_name": "Test Special Express (Updated)",
            "from_district": "Dhaka",
            "to_district": "Chattogram",
            "off_day": "Friday",
            "departure": "08:30:00",
            "arrival": "14:30:00",
            "day_offset": 0,
        },
        headers=auth_header,
    )
    assert update_resp.status_code == 200

    # Delete the test train service
    del_resp = client.delete(f"/api/admin/train-services/{srv_id}", headers=auth_header)
    assert del_resp.status_code == 204

    # Verify removal
    list_resp2 = client.get("/api/admin/train-services", headers=auth_header)
    assert not any(s["train_no"] == "9999" for s in list_resp2.json())


def test_multimodal_single_and_sensible_without_detour(client: TestClient):
    travel_date = (date.today() + timedelta(days=1)).isoformat()
    # Search Dhaka -> Chattogram at 12:00
    response = client.post(
        "/api/search",
        json={
            "origin": "Dhaka",
            "destination": "Chattogram",
            "travel_date": travel_date,
            "departure_time": "12:00",
            "preference": "fastest",
        },
    )
    assert response.status_code == 200
    data = response.json()
    multimodal_routes = [r for r in data["routes"] if r["kind"] == "multimodal"]

    # At most a single multimodal route shown
    assert len(multimodal_routes) <= 1

    # Route must make geographic sense without detour to Rajshahi or Sylhet
    for mr in multimodal_routes:
        assert "Rajshahi" not in mr["path"]
        assert "Sylhet" not in mr["path"]
        assert "Dinajpur" not in mr["path"]
        assert "Bogura" not in mr["path"]


def test_chapai_and_alias_search_returns_bus_train_and_multimodal(client: TestClient):
    travel_date = (date.today() + timedelta(days=1)).isoformat()
    for dest in ["Chapai", "Chapai Nawabganj", "Chapainawabganj"]:
        response = client.post(
            "/api/search",
            json={
                "origin": "Dhaka",
                "destination": dest,
                "travel_date": travel_date,
                "departure_time": "06:00",
                "preference": "balanced",
            },
        )
        assert response.status_code == 200, f"Failed for {dest}"
        data = response.json()
        kinds = {r["kind"] for r in data["routes"]}
        assert "train" in kinds, f"Train missing for {dest}"
        assert "bus" in kinds, f"Bus missing for {dest}"
        assert "multimodal" in kinds, f"Multimodal missing for {dest}"


