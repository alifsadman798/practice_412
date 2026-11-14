import pytest
from datetime import date, timedelta


def test_user_registration_success(client):
    res = client.post(
        "/api/auth/register",
        json={
            "full_name": "Rahim Ahmed",
            "email": "rahim@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert "user" in data
    user = data["user"]
    assert user["full_name"] == "Rahim Ahmed"
    assert user["email"] == "rahim@example.com"
    assert user["user_id"].startswith("SRU-")
    assert len(user["user_id"]) == 12

    # Verify user starts with zero notifications
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    notif_res = client.get("/api/user/notifications", headers=headers)
    assert notif_res.status_code == 200
    assert notif_res.json() == []


def test_user_registration_duplicate_email(client):
    payload = {
        "full_name": "Duplicate User",
        "email": "dup@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


def test_user_registration_password_mismatch(client):
    res = client.post(
        "/api/auth/register",
        json={
            "full_name": "Bad User",
            "email": "bad@example.com",
            "password": "Password123",
            "confirm_password": "DifferentPassword",
        },
    )
    assert res.status_code == 422


def test_user_login_and_auth_profile(client):
    client.post(
        "/api/auth/register",
        json={
            "full_name": "Karim Ullah",
            "email": "karim@example.com",
            "password": "SecretPassword123",
            "confirm_password": "SecretPassword123",
        },
    )

    # Valid Login
    login_res = client.post(
        "/api/auth/login",
        json={"email": "karim@example.com", "password": "SecretPassword123"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Invalid Login
    bad_login = client.post(
        "/api/auth/login",
        json={"email": "karim@example.com", "password": "WrongPassword"},
    )
    assert bad_login.status_code == 401

    # Check /me
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "karim@example.com"

    # Update profile name
    update_res = client.put(
        "/api/auth/profile",
        json={"full_name": "Karim Ullah Updated"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["full_name"] == "Karim Ullah Updated"

    # Change password
    pw_res = client.put(
        "/api/auth/change-password",
        json={
            "current_password": "SecretPassword123",
            "new_password": "BrandNewPassword456",
            "confirm_password": "BrandNewPassword456",
        },
        headers=headers,
    )
    assert pw_res.status_code == 200


def test_user_preferences_and_favourites(client):
    reg = client.post(
        "/api/auth/register",
        json={
            "full_name": "Traveler One",
            "email": "traveler1@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
        },
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Preferences
    pref_res = client.get("/api/user/preferences", headers=headers)
    assert pref_res.status_code == 200
    assert pref_res.json()["default_transport"] == "No Preference"

    pref_update = client.put(
        "/api/user/preferences",
        json={"default_transport": "Train", "default_preference": "fastest"},
        headers=headers,
    )
    assert pref_update.status_code == 200
    assert pref_update.json()["default_transport"] == "Train"
    assert pref_update.json()["default_preference"] == "fastest"

    # Favourite Routes
    add_route = client.post(
        "/api/user/favourites/routes",
        json={"origin": "Dhaka", "destination": "Chattogram"},
        headers=headers,
    )
    assert add_route.status_code == 201
    route_id = add_route.json()["id"]

    routes_list = client.get("/api/user/favourites/routes", headers=headers)
    assert routes_list.status_code == 200
    assert len(routes_list.json()) == 1
    assert routes_list.json()[0]["origin"] == "Dhaka"

    # Delete favourite route
    del_route = client.delete(f"/api/user/favourites/routes/{route_id}", headers=headers)
    assert del_route.status_code == 204

    # Favourite Services
    add_srv = client.post(
        "/api/user/favourites/services",
        json={
            "transport_type": "train",
            "service_identifier": "702",
            "service_name": "Suborna Express",
        },
        headers=headers,
    )
    assert add_srv.status_code == 201
    srv_id = add_srv.json()["id"]

    srv_list = client.get("/api/user/favourites/services", headers=headers)
    assert srv_list.status_code == 200
    assert len(srv_list.json()) == 1

    del_srv = client.delete(f"/api/user/favourites/services/{srv_id}", headers=headers)
    assert del_srv.status_code == 204



def test_admin_transport_mutations_and_audit_logs(client):
    """Verifies that remaining administrative transport CRUD operations work and create audit logs."""
    admin_auth = ("admin", "12345678")

    # Add a bus schedule via admin
    add_res = client.post(
        "/api/admin/bus-schedules",
        json={
            "route_id": "TEST-BUS-99",
            "from_district": "Dhaka",
            "to_district": "Sylhet",
            "transport_name": "Test Green Line",
            "departure": "08:30:00",
            "arrival": "14:30:00",
            "fare": 650,
        },
        auth=admin_auth,
    )
    assert add_res.status_code == 201
    sched_id = add_res.json()["id"]

    # Verify audit log was created for bus schedule creation
    audit_res = client.get("/api/admin/audit-logs", auth=admin_auth)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert any(
        l["action"] == "CREATE_BUS_SCHEDULE" and l["target_type"] == "BusSchedule"
        for l in logs
    )

    # Clean up test schedule
    del_res = client.delete(f"/api/admin/bus-schedules/{sched_id}", auth=admin_auth)
    assert del_res.status_code == 204
