import pytest
from fastapi.testclient import TestClient


def test_user_report_submission_pending_and_admin_verify(client: TestClient):
    """
    Verification points 1-5:
    1. Normal user submits report (status PENDING).
    2. Report appears in admin list.
    3. Admin verifies report -> status VERIFIED.
    4. User receives verified notification.
    5. User sees VERIFIED in report history.
    """
    # 1. Register and login normal user
    reg = client.post(
        "/api/auth/register",
        json={
            "full_name": "Test Reporter",
            "email": "reporter1@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
        },
    )
    assert reg.status_code == 201
    user_token = reg.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    admin_auth = ("admin", "12345678")

    # User submits a report
    sub_res = client.post(
        "/api/user/reports",
        json={
            "category": "Incorrect Bus Fare",
            "title": "Bus fare Dhaka to Cumilla is 350 BDT, not 300",
            "description": "I traveled yesterday with Hanif and the counter charged 350 BDT.",
            "transport_mode": "Bus",
            "related_route_info": "Dhaka to Cumilla",
        },
        headers=user_headers,
    )
    assert sub_res.status_code == 201
    rep_data = sub_res.json()
    report_id = rep_data["report_id"]
    assert report_id.startswith("REP-")
    assert rep_data["status"] == "PENDING"
    assert rep_data["category"] == "Incorrect Bus Fare"

    # 2. Admin views report list
    admin_list_res = client.get("/api/admin/reports?status=PENDING", auth=admin_auth)
    assert admin_list_res.status_code == 200
    reports = admin_list_res.json()
    assert any(r["report_id"] == report_id for r in reports)

    # 3. Admin verifies report with note
    verify_res = client.post(
        f"/api/admin/reports/{report_id}/verify",
        json={"admin_response": "Thank you! Verified with operator counter and updated in schedules."},
        auth=admin_auth,
    )
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["status"] == "VERIFIED"
    assert v_data["reviewed_by"] == "admin"
    assert "Verified with operator" in v_data["admin_response"]

    # 4. User receives verified notification
    notifs_res = client.get("/api/user/notifications", headers=user_headers)
    assert notifs_res.status_code == 200
    notifs = notifs_res.json()
    assert len(notifs) >= 1
    verify_notif = next((n for n in notifs if n["report_id"] == report_id), None)
    assert verify_notif is not None
    assert verify_notif["notification_type"] == "REPORT_VERIFIED"
    assert verify_notif["is_read"] is False
    assert "verified" in verify_notif["message"].lower()

    # User marks notification as read
    read_res = client.put(f"/api/user/notifications/{verify_notif['id']}/read", headers=user_headers)
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True

    # 5. User checks report in history
    hist_res = client.get(f"/api/user/reports/{report_id}", headers=user_headers)
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["status"] == "VERIFIED"
    assert hist_data["admin_response"] == "Thank you! Verified with operator counter and updated in schedules."


def test_user_report_rejection_with_reason(client: TestClient):
    """
    Verification points 6-8:
    6. Report submitted and rejected with reason -> status REJECTED.
    7. User receives rejection notification with reason.
    8. User sees REJECTED in report history.
    """
    reg = client.post(
        "/api/auth/register",
        json={
            "full_name": "Second User",
            "email": "user2@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
        },
    )
    user_token = reg.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    admin_auth = ("admin", "12345678")

    # Submit second report
    sub_res = client.post(
        "/api/user/reports",
        json={
            "category": "Wrong Departure Time",
            "title": "Subarna Express departs at 10:00 PM",
            "description": "I believe the train departs at night instead of morning.",
            "transport_mode": "Train",
            "related_route_info": "Subarna Express (701)",
        },
        headers=user_headers,
    )
    assert sub_res.status_code == 201
    report_id = sub_res.json()["report_id"]

    # Rejection requires reason: missing or empty reason should fail
    bad_reject = client.post(
        f"/api/admin/reports/{report_id}/reject",
        json={"admin_response": "   "},
        auth=admin_auth,
    )
    assert bad_reject.status_code == 422

    # Reject with valid mandatory reason
    rejection_reason = "Official railway timetable confirms Subarna Express departs at 16:30. 10:00 PM is inaccurate."
    reject_res = client.post(
        f"/api/admin/reports/{report_id}/reject",
        json={"admin_response": rejection_reason},
        auth=admin_auth,
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "REJECTED"

    # 7. User receives rejection notification
    notifs_res = client.get("/api/user/notifications", headers=user_headers)
    assert notifs_res.status_code == 200
    reject_notif = next((n for n in notifs_res.json() if n["report_id"] == report_id), None)
    assert reject_notif is not None
    assert reject_notif["notification_type"] == "REPORT_REJECTED"
    assert rejection_reason in reject_notif["message"]

    # 8. User sees REJECTED in report history
    hist_res = client.get(f"/api/user/reports/{report_id}", headers=user_headers)
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["status"] == "REJECTED"
    assert hist_data["admin_response"] == rejection_reason


def test_soft_delete_user_and_admin_histories_and_audit(client: TestClient):
    """
    Verification points 9-11:
    9. User deletes report from own history -> soft-deleted for user (user_deleted=True).
    10. Admin deletes report from admin history -> soft-deleted for admin (admin_deleted=True).
    11. Audit logs remain intact and queryable by admin.
    """
    reg = client.post(
        "/api/auth/register",
        json={
            "full_name": "History User",
            "email": "history_user@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
        },
    )
    user_token = reg.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    admin_auth = ("admin", "12345678")

    sub_res = client.post(
        "/api/user/reports",
        json={
            "category": "Broken Functionality",
            "title": "Button was slow",
            "description": "Search button took 3 seconds.",
            "transport_mode": "General",
        },
        headers=user_headers,
    )
    report_id = sub_res.json()["report_id"]

    # 9. User deletes report from own history
    del_res = client.delete(f"/api/user/reports/{report_id}", headers=user_headers)
    assert del_res.status_code == 200

    # User cannot see it anymore in /api/user/reports
    user_list = client.get("/api/user/reports", headers=user_headers).json()
    assert not any(r["report_id"] == report_id for r in user_list)
    assert client.get(f"/api/user/reports/{report_id}", headers=user_headers).status_code == 404

    # But it is still preserved and visible to admin
    admin_list = client.get("/api/admin/reports?include_deleted=true", auth=admin_auth).json()
    admin_rep = next((r for r in admin_list if r["report_id"] == report_id), None)
    assert admin_rep is not None
    assert admin_rep["user_deleted"] is True
    assert admin_rep["admin_deleted"] is False

    # 10. Admin deletes report from admin visible history
    admin_del_res = client.delete(f"/api/admin/reports/{report_id}", auth=admin_auth)
    assert admin_del_res.status_code == 200

    # Without include_deleted, it is hidden from admin list
    admin_list_active = client.get("/api/admin/reports", auth=admin_auth).json()
    assert not any(r["report_id"] == report_id for r in admin_list_active)

    # With include_deleted=true, it is still preserved in database
    admin_list_all = client.get("/api/admin/reports?include_deleted=true", auth=admin_auth).json()
    admin_rep_after = next((r for r in admin_list_all if r["report_id"] == report_id), None)
    assert admin_rep_after is not None
    assert admin_rep_after["admin_deleted"] is True

    # 11. Audit logs remain intact and queryable
    audit_res = client.get("/api/admin/audit-logs", auth=admin_auth)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    actions = [l["action"] for l in logs if l.get("target_id") == report_id]
    assert "SUBMIT_REPORT" in actions
    assert "USER_DELETE_REPORT_HISTORY" in actions
    assert any("ADMIN_DELETE_REPORT" in a for a in actions)


def test_admin_warning_and_blocking_workflow(client: TestClient):
    """
    Verification points 12-17:
    12. Admin issues warning to user.
    13. User receives warning notification.
    14. Admin blocks user -> is_blocked=True.
    15. Blocked user cannot submit new reports (403 Forbidden).
    16. Admin unblocks user -> is_blocked=False.
    17. User can submit reports again.
    """
    reg = client.post(
        "/api/auth/register",
        json={
            "full_name": "Moderated Citizen",
            "email": "mod_citizen@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
        },
    )
    user_data = reg.json()["user"]
    user_id = user_data["user_id"]
    user_token = reg.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    admin_auth = ("admin", "12345678")

    # 12. Admin issues warning to user
    warn_res = client.post(
        f"/api/admin/users/{user_id}/warn",
        json={"reason": "Please refrain from submitting test or joke reports."},
        auth=admin_auth,
    )
    assert warn_res.status_code == 201
    assert warn_res.json()["user_id"] == user_id

    # Admin checks user warnings list
    warnings_list_res = client.get(f"/api/admin/users/{user_id}/warnings", auth=admin_auth)
    assert warnings_list_res.status_code == 200
    assert len(warnings_list_res.json()) >= 1

    # 13. User receives warning notification
    notifs_res = client.get("/api/user/notifications", headers=user_headers)
    assert notifs_res.status_code == 200
    warn_notif = next((n for n in notifs_res.json() if n["notification_type"] == "ADMIN_WARNING"), None)
    assert warn_notif is not None
    assert "test or joke" in warn_notif["message"]

    # 14. Admin blocks user
    block_res = client.post(
        f"/api/admin/users/{user_id}/block",
        json={"reason": "Repeated policy violations after official warning."},
        auth=admin_auth,
    )
    assert block_res.status_code == 200
    assert block_res.json()["user"]["is_blocked"] is True

    # User profile shows blocked status
    me_res = client.get("/api/auth/me", headers=user_headers)
    assert me_res.status_code == 200
    assert me_res.json()["is_blocked"] is True
    assert "Repeated policy violations" in me_res.json()["blocked_reason"]

    # 15. Blocked user CANNOT submit new reports -> 403 Forbidden
    blocked_sub = client.post(
        "/api/user/reports",
        json={
            "category": "Incorrect Bus Fare",
            "title": "Blocked user trying to submit",
            "description": "This should be rejected by security dependency.",
            "transport_mode": "Bus",
        },
        headers=user_headers,
    )
    assert blocked_sub.status_code == 403
    assert "restricted" in blocked_sub.json()["detail"].lower()

    # 16. Admin unblocks user
    unblock_res = client.post(
        f"/api/admin/users/{user_id}/unblock",
        json={"reason": "User contacted support and agreed to terms."},
        auth=admin_auth,
    )
    assert unblock_res.status_code == 200
    assert unblock_res.json()["user"]["is_blocked"] is False

    # Block history audit contains both BLOCK and UNBLOCK entries
    block_hist_res = client.get(f"/api/admin/users/{user_id}/block-history", auth=admin_auth)
    assert block_hist_res.status_code == 200
    actions = [h["action"] for h in block_hist_res.json()]
    assert "BLOCK" in actions
    assert "UNBLOCK" in actions

    # 17. User can submit reports again
    resubmit = client.post(
        "/api/user/reports",
        json={
            "category": "General Complaint or Suggestion",
            "title": "Now I am unblocked",
            "description": "Legitimate helpful suggestion for bus routes in Sylhet.",
            "transport_mode": "Bus",
        },
        headers=user_headers,
    )
    assert resubmit.status_code == 201
    assert resubmit.json()["status"] == "PENDING"


def test_cross_user_isolation_and_admin_security(client: TestClient):
    """
    Verification points 18-19:
    18. Unauthorized users cannot access admin endpoints (401/403).
    19. Users cannot view/delete other users' reports (404).
    """
    # User A
    user_a = client.post(
        "/api/auth/register",
        json={
            "full_name": "User Alpha",
            "email": "alpha@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
        },
    ).json()
    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}

    # User B
    user_b = client.post(
        "/api/auth/register",
        json={
            "full_name": "User Beta",
            "email": "beta@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
        },
    ).json()
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}

    # 18. Normal user cannot access admin endpoints
    assert client.get("/api/admin/reports", headers=headers_a).status_code in (401, 403)
    assert client.get("/api/admin/users", headers=headers_a).status_code in (401, 403)
    assert client.post("/api/admin/users/test/warn", json={"reason": "foo"}, headers=headers_a).status_code in (401, 403)

    # User A creates a report
    rep_a = client.post(
        "/api/user/reports",
        json={
            "category": "Route Information",
            "title": "Private report by A",
            "description": "Only user A should see this in their history.",
            "transport_mode": "Train",
        },
        headers=headers_a,
    ).json()
    rep_a_id = rep_a["report_id"]

    # 19. User B cannot view User A's report -> 404
    assert client.get(f"/api/user/reports/{rep_a_id}", headers=headers_b).status_code == 404

    # User B cannot delete User A's report -> 404
    assert client.delete(f"/api/user/reports/{rep_a_id}", headers=headers_b).status_code == 404


def test_core_routing_remains_fully_operational(client: TestClient):
    """
    Verification point 20:
    20. Core route search, bus, and train routing remain fully operational.
    """
    res = client.post(
        "/api/search",
        json={
            "origin": "Dhaka",
            "destination": "Cumilla",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "routes" in data
    assert len(data["routes"]) > 0

    # Timetable searches
    bus_res = client.get("/api/timetables/bus?origin=Dhaka&destination=Gazipur")
    assert bus_res.status_code == 200
    assert len(bus_res.json()) > 0

    train_res = client.get("/api/timetables/train?origin=Dhaka&destination=Sylhet")
    assert train_res.status_code == 200
    assert len(train_res.json()) > 0


def test_frontend_ui_elements_present():
    """Verifies that all required HTML UI elements for user reports and admin management are present in templates."""
    with open("static/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    assert "notif-btn" in html
    assert "notif-count-badge" in html
    assert 'data-dash-tab="reports"' in html
    assert 'data-dash-tab="notifications"' in html
    assert "dash-pane-reports" in html
    assert "dash-pane-notifications" in html
    assert "report-modal" in html
    assert "report-form" in html
    assert "report-detail-modal" in html
    assert "profile-blocked-banner" in html

    with open("static/admin.html", "r", encoding="utf-8") as f:
        admin_html = f.read()

    assert 'data-admin-tab="reports"' in admin_html
    assert 'data-admin-tab="users"' in admin_html
    assert "tab-pane-reports" in admin_html
    assert "tab-pane-users" in admin_html
    assert "admin-report-modal" in admin_html
    assert "admin-warn-modal" in admin_html
    assert "admin-block-modal" in admin_html
    assert "admin-block-history-modal" in admin_html
