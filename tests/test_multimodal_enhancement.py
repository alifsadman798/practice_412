from fastapi.testclient import TestClient
from src.api.main import app

def test_multimodal_transfer_guidance_and_alerts(client: TestClient):
    res = client.post("/api/search", json={"origin": "Dhaka", "destination": "Sylhet"})
    assert res.status_code == 200
    data = res.json()

    # Find multimodal route
    mm_routes = [r for r in data["routes"] if r["kind"] == "multimodal"]
    assert len(mm_routes) >= 1
    route = mm_routes[0]

    # Verify legs are present
    assert len(route["legs"]) >= 2
    leg1 = route["legs"][0]
    leg2 = route["legs"][1]

    # Verify transfer guidance is attached
    assert leg1["transfer_to_next"] is not None
    tr = leg1["transfer_to_next"]
    assert "from_location" in tr
    assert "to_location" in tr
    assert "travel_minutes" in tr
    assert tr["travel_minutes"] > 0
    assert "target_arrival_time" in tr

    # Verify time sensitive connection alerts in warnings
    has_alert = any("Connection Alert" in w for w in route["warnings"])
    assert has_alert, "Expected Connection Alert in route warnings"


def test_bus_and_train_only_routes_remain_intact(client: TestClient):
    res = client.post("/api/search", json={"origin": "Dhaka", "destination": "Chattogram"})
    assert res.status_code == 200
    data = res.json()

    bus_routes = [r for r in data["routes"] if r["kind"] == "bus"]
    train_routes = [r for r in data["routes"] if r["kind"] == "train"]

    assert len(bus_routes) >= 1
    assert len(train_routes) >= 1

    # Single leg routes don't have transfer_to_next
    for r in bus_routes:
        if len(r["legs"]) == 1:
            assert r["legs"][0]["transfer_to_next"] is None
