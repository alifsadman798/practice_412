import pytest
from fastapi.testclient import TestClient


ADMIN_AUTH = ("admin", "12345678")


def test_admin_disruption_auth_and_candidates(client: TestClient):
    """Verifies authentication requirements and segment candidate lookup."""
    # 1. Unauthenticated request must return 401
    unauth = client.get("/api/admin/disruptions")
    assert unauth.status_code == 401

    unauth_create = client.post("/api/admin/disruptions", json={"title": "Test"})
    assert unauth_create.status_code == 401

    # 2. Segment candidates returns road edges and rail stations
    cand_res = client.get("/api/admin/disruptions/segments/candidates", auth=ADMIN_AUTH)
    assert cand_res.status_code == 200
    cand_data = cand_res.json()
    assert "road_segments" in cand_data
    assert "rail_stations" in cand_data
    assert len(cand_data["road_segments"]) > 0
    assert len(cand_data["rail_stations"]) > 0


def test_disruption_lifecycle_crud_and_audit(client: TestClient):
    """Tests the full admin lifecycle: create, update, activate, deactivate, resolve, cancel, audit, and soft-delete."""
    # 1. Create a draft disruption
    create_payload = {
        "title": "Severe flooding on Dhaka-Cumilla highway",
        "location_name": "Cumilla",
        "transport_mode": "BUS",
        "cause": "FLOOD",
        "severity": "HIGH",
        "description": "Flash flooding over road segments in Cumilla near Daudkandi.",
        "alert_message": "Heavy flooding on highway. Bus trips delayed by up to 2 hours.",
        "status": "DRAFT",
        "source_name": "RHD Bangladesh",
        "source_url": "https://rhd.gov.bd",
        "admin_notes": "Monitored via control room.",
        "affected_segments": [
            {
                "transport_mode": "BUS",
                "affected_segment_id": "edge:Dhaka-Cumilla",
                "segment_description": "Dhaka ↔ Cumilla Highway",
                "from_point": "Dhaka",
                "to_point": "Cumilla",
            }
        ],
    }
    create_res = client.post("/api/admin/disruptions", json=create_payload, auth=ADMIN_AUTH)
    assert create_res.status_code == 201
    created = create_res.json()
    dis_id = created["disruption_id"]
    assert dis_id.startswith("DIS-")
    assert created["status"] == "DRAFT"
    assert created["severity"] == "HIGH"
    assert len(created["affected_segments"]) == 1

    # 2. Get disruption details
    detail_res = client.get(f"/api/admin/disruptions/{dis_id}", auth=ADMIN_AUTH)
    assert detail_res.status_code == 200
    assert detail_res.json()["title"] == create_payload["title"]

    # 3. Update disruption
    update_res = client.put(
        f"/api/admin/disruptions/{dis_id}",
        json={
            "title": "Severe flash flood on Dhaka-Cumilla highway (Updated)",
            "severity": "CRITICAL",
            "alert_message": "Highway closed due to rising water level. Avoid travel.",
        },
        auth=ADMIN_AUTH,
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["severity"] == "CRITICAL"
    assert "Updated" in updated["title"]

    # 4. Status transitions: Activate
    act_res = client.post(f"/api/admin/disruptions/{dis_id}/activate", auth=ADMIN_AUTH)
    assert act_res.status_code == 200
    assert act_res.json()["status"] == "ACTIVE"
    assert act_res.json()["activated_at"] is not None

    # Deactivate
    deact_res = client.post(f"/api/admin/disruptions/{dis_id}/deactivate", auth=ADMIN_AUTH)
    assert deact_res.status_code == 200
    assert deact_res.json()["status"] == "INACTIVE"

    # Resolve
    res_res = client.post(f"/api/admin/disruptions/{dis_id}/resolve", auth=ADMIN_AUTH)
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"
    assert res_res.json()["resolved_at"] is not None

    # Cancel
    canc_res = client.post(f"/api/admin/disruptions/{dis_id}/cancel", auth=ADMIN_AUTH)
    assert canc_res.status_code == 200
    assert canc_res.json()["status"] == "CANCELLED"

    # 5. Audit logs inspection
    audit_res = client.get(f"/api/admin/disruptions/{dis_id}/audit-logs", auth=ADMIN_AUTH)
    assert audit_res.status_code == 200
    audit_logs = audit_res.json()
    actions = [a["action"] for a in audit_logs]
    assert "CREATED" in actions
    assert "EDITED" in actions
    assert "ACTIVATED" in actions
    assert "DEACTIVATED" in actions
    assert "RESOLVED" in actions
    assert "CANCELLED" in actions

    # 6. Soft delete
    del_res = client.delete(f"/api/admin/disruptions/{dis_id}", auth=ADMIN_AUTH)
    assert del_res.status_code == 200

    # Verify not returned in normal list, but returned when include_deleted=true
    list_res = client.get("/api/admin/disruptions", auth=ADMIN_AUTH)
    ids = [d["disruption_id"] for d in list_res.json()]
    assert dis_id not in ids

    list_all = client.get("/api/admin/disruptions?include_deleted=true", auth=ADMIN_AUTH)
    all_ids = [d["disruption_id"] for d in list_all.json()]
    assert dis_id in all_ids


def test_bus_only_disruption_in_cumilla(client: TestClient):
    """
    Scenario: Bus-only disruption in Cumilla.
    Bus routes traversing Cumilla are marked affected; train routes remain unaffected.
    """
    create_res = client.post(
        "/api/admin/disruptions",
        json={
            "title": "Road blockage in Cumilla Highway",
            "location_name": "Cumilla",
            "transport_mode": "BUS",
            "cause": "ROAD_BLOCKAGE",
            "severity": "HIGH",
            "description": "Protest near Cumilla bypass blocking bus movement.",
            "alert_message": "Bus service delayed along Cumilla corridor.",
            "status": "ACTIVE",
            "affected_segments": [
                {
                    "transport_mode": "BUS",
                    "affected_segment_id": "edge:Dhaka-Cumilla",
                    "segment_description": "Dhaka-Cumilla Road",
                    "from_point": "Dhaka",
                    "to_point": "Cumilla",
                }
            ],
        },
        auth=ADMIN_AUTH,
    )
    assert create_res.status_code == 201
    dis_id = create_res.json()["disruption_id"]

    try:
        # Search route Dhaka -> Cumilla
        search_res = client.post("/api/search", json={"origin": "Dhaka", "destination": "Cumilla"})
        assert search_res.status_code == 200
        routes = search_res.json()["routes"]

        bus_routes = [r for r in routes if r["kind"].upper() == "BUS"]
        train_routes = [r for r in routes if r["kind"].upper() == "TRAIN"]

        assert len(bus_routes) > 0
        for b_route in bus_routes:
            assert b_route["is_affected"] is True
            assert len(b_route["disruption_alerts"]) >= 1
            alert = b_route["disruption_alerts"][0]
            assert alert["disruption_id"] == dis_id
            assert alert["transport_mode"] == "BUS"
            assert alert["cause"] == "ROAD_BLOCKAGE"

        # Train routes (if any) must remain unaffected
        for t_route in train_routes:
            assert t_route["is_affected"] is False
            assert len(t_route["disruption_alerts"]) == 0
    finally:
        client.delete(f"/api/admin/disruptions/{dis_id}", auth=ADMIN_AUTH)


def test_train_only_disruption_in_cumilla(client: TestClient):
    """
    Scenario: Train-only disruption in Cumilla.
    Trains between Dhaka and Noakhali (stopping in Cumilla) are affected.
    Bus routes between Dhaka and Cumilla are unaffected.
    Trains between Dhaka and Sylhet (which do not pass Cumilla) are unaffected.
    """
    create_res = client.post(
        "/api/admin/disruptions",
        json={
            "title": "Railway signal failure at Cumilla Station",
            "location_name": "Cumilla",
            "transport_mode": "TRAIN",
            "cause": "RAILWAY_ACCIDENT",
            "severity": "MODERATE",
            "description": "Signal failure causing train halt at Cumilla.",
            "alert_message": "Train departures through Cumilla may face delays.",
            "status": "ACTIVE",
            "affected_segments": [
                {
                    "transport_mode": "TRAIN",
                    "affected_segment_id": "station:Cumilla",
                    "segment_description": "Cumilla Railway Station",
                    "from_point": "Cumilla",
                    "to_point": None,
                }
            ],
        },
        auth=ADMIN_AUTH,
    )
    assert create_res.status_code == 201
    dis_id = create_res.json()["disruption_id"]

    try:
        # 1. Search Dhaka -> Noakhali (Upakul Express train stops at Cumilla station)
        search_noa = client.post("/api/search", json={"origin": "Dhaka", "destination": "Noakhali"})
        assert search_noa.status_code == 200
        noa_routes = search_noa.json()["routes"]

        noa_trains = [r for r in noa_routes if r["kind"].upper() == "TRAIN"]
        noa_buses = [r for r in noa_routes if r["kind"].upper() == "BUS"]

        # Train routes through Cumilla must be marked affected
        assert len(noa_trains) > 0
        for t_route in noa_trains:
            assert t_route["is_affected"] is True
            assert any(a["disruption_id"] == dis_id for a in t_route["disruption_alerts"])

        # Bus routes must NOT be affected by the train disruption
        for b_route in noa_buses:
            assert b_route["is_affected"] is False
            assert len(b_route["disruption_alerts"]) == 0

        # 2. Search Dhaka -> Sylhet (train line does not pass Cumilla)
        search_syl = client.post("/api/search", json={"origin": "Dhaka", "destination": "Sylhet"})
        assert search_syl.status_code == 200
        syl_routes = search_syl.json()["routes"]
        syl_trains = [r for r in syl_routes if r["kind"].upper() == "TRAIN"]
        for t_route in syl_trains:
            assert t_route["is_affected"] is False
            assert len(t_route["disruption_alerts"]) == 0

    finally:
        client.delete(f"/api/admin/disruptions/{dis_id}", auth=ADMIN_AUTH)


def test_multimodal_leg_isolation(client: TestClient):
    """
    Scenario: In a multimodal route, only the leg traversing the affected mode/segment
    is marked is_affected=True; unaffected legs remain is_affected=False.
    """
    create_res = client.post(
        "/api/admin/disruptions",
        json={
            "title": "Train engine trouble at Brahmanbaria",
            "location_name": "Brahmanbaria",
            "transport_mode": "TRAIN",
            "cause": "OTHER",
            "severity": "MODERATE",
            "description": "Engine trouble causing speed restriction.",
            "alert_message": "Train leg delayed.",
            "status": "ACTIVE",
            "affected_segments": [
                {
                    "transport_mode": "TRAIN",
                    "affected_segment_id": "station:Brahmanbaria",
                    "segment_description": "Brahmanbaria Railway Station",
                    "from_point": "Brahmanbaria",
                    "to_point": None,
                }
            ],
        },
        auth=ADMIN_AUTH,
    )
    assert create_res.status_code == 201
    dis_id = create_res.json()["disruption_id"]

    try:
        search_res = client.post("/api/search", json={"origin": "Dhaka", "destination": "Sylhet"})
        assert search_res.status_code == 200
        routes = search_res.json()["routes"]
        mm_routes = [r for r in routes if r["kind"].upper() == "MULTIMODAL" and len(r["legs"]) > 1]

        if mm_routes:
            mm = mm_routes[0]
            # Verify individual legs: only train leg traversing Brahmanbaria is affected
            for leg in mm["legs"]:
                if leg["mode"].upper() == "TRAIN":
                    stops_names = [s["station"] for s in leg.get("stops", [])] + [leg["origin"], leg["destination"]]
                    if any("brahmanbaria" in s.lower() for s in stops_names):
                        assert leg["is_affected"] is True
                        assert any(a["disruption_id"] == dis_id for a in leg["disruption_alerts"])
                elif leg["mode"].upper() == "BUS" or leg["mode"].upper() == "LOCAL":
                    assert leg["is_affected"] is False
                    assert len(leg["disruption_alerts"]) == 0
    finally:
        client.delete(f"/api/admin/disruptions/{dis_id}", auth=ADMIN_AUTH)


def test_routing_non_regression_guarantee(client: TestClient):
    """
    CRITICAL NON-REGRESSION TEST:
    Verifies that the presence of an active transport disruption does NOT alter:
    - Route paths
    - Distances (km)
    - Fares (BDT)
    - Journey durations (expected_minutes)
    - Number of transfers
    - Overall route rankings
    """
    # 1. Search clean baseline without disruptions
    baseline_res = client.post("/api/search", json={"origin": "Dhaka", "destination": "Chittagong"})
    assert baseline_res.status_code == 200
    baseline_routes = baseline_res.json()["routes"]

    # 2. Add a critical road disruption
    dis_res = client.post(
        "/api/admin/disruptions",
        json={
            "title": "Major Highway Blockade",
            "location_name": "Cumilla",
            "transport_mode": "BUS",
            "cause": "ROAD_CLOSURE",
            "severity": "CRITICAL",
            "description": "Complete highway closure.",
            "alert_message": "Road completely closed.",
            "status": "ACTIVE",
            "affected_segments": [
                {
                    "transport_mode": "BUS",
                    "affected_segment_id": "edge:Dhaka-Cumilla",
                    "segment_description": "Dhaka - Cumilla Road",
                    "from_point": "Dhaka",
                    "to_point": "Cumilla",
                }
            ],
        },
        auth=ADMIN_AUTH,
    )
    dis_id = dis_res.json()["disruption_id"]

    try:
        # 3. Search with active disruption
        disrupted_res = client.post("/api/search", json={"origin": "Dhaka", "destination": "Chittagong"})
        assert disrupted_res.status_code == 200
        disrupted_routes = disrupted_res.json()["routes"]

        assert len(disrupted_routes) == len(baseline_routes)

        for base_r, disp_r in zip(baseline_routes, disrupted_routes):
            # Paths must be 100% identical
            assert base_r["path"] == disp_r["path"]
            # Distances must be 100% identical
            assert base_r["distance_km"] == disp_r["distance_km"]
            # Fares must be 100% identical
            assert base_r["fare_bdt"] == disp_r["fare_bdt"]
            # Travel times must be 100% identical
            assert base_r["travel_time"]["expected_minutes"] == disp_r["travel_time"]["expected_minutes"]
            # Transfers must be 100% identical
            assert base_r["transfers"] == disp_r["transfers"]
            # Route kinds and ordering must be identical
            assert base_r["kind"] == disp_r["kind"]

    finally:
        client.delete(f"/api/admin/disruptions/{dis_id}", auth=ADMIN_AUTH)


def test_nlp_extraction_and_clarification(client: TestClient):
    """
    Tests automated extraction of location, transport mode, incident type,
    operational impact, and automatic route detection with ambiguity detection.
    """
    # 1. Train incident near Cumilla
    train_text = "A railway accident has occurred near Cumilla, causing train movement to be suspended on the affected railway section until further notice."
    res1 = client.post("/api/admin/disruptions/analyze", json={"description": train_text}, auth=ADMIN_AUTH)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "READY"
    assert data1["extracted"]["location"] == "Cumilla"
    assert data1["extracted"]["transport_mode"] == "TRAIN"
    assert "Railway Accident" in data1["extracted"]["incident_type"]
    assert "Suspended" in data1["extracted"]["operational_impact"]
    assert data1["extracted"]["matching_confidence"] == "HIGH"
    assert data1["extracted"]["matching_status"] == "CONFIDENT MATCH"
    assert data1["total_affected_routes"] > 0
    for r in data1["affected_routes"]:
        assert r["mode"] == "TRAIN"

    # 2. Road accident near Cumilla blocking highway
    road_text = "A major road accident near Cumilla has blocked the Dhaka–Chittagong highway. Bus movement is currently disrupted."
    res2 = client.post("/api/admin/disruptions/analyze", json={"description": road_text}, auth=ADMIN_AUTH)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "READY"
    assert data2["extracted"]["location"] == "Cumilla"
    assert data2["extracted"]["transport_mode"] == "BUS"
    assert data2["extracted"]["matching_confidence"] == "HIGH"
    assert data2["extracted"]["matching_status"] == "CONFIDENT MATCH"
    assert data2["total_affected_routes"] > 0
    for r in data2["affected_routes"]:
        assert r["mode"] == "BUS"

    # 3. Both modes disrupted
    both_text = "Severe flooding near Cumilla has disrupted both road and railway movement."
    res3 = client.post("/api/admin/disruptions/analyze", json={"description": both_text}, auth=ADMIN_AUTH)
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["status"] == "READY"
    assert data3["extracted"]["location"] == "Cumilla"
    assert data3["extracted"]["transport_mode"] == "BOTH"
    modes_detected = {r["mode"] for r in data3["affected_routes"]}
    assert "TRAIN" in modes_detected
    assert "BUS" in modes_detected

    # 4. Location correction override in analyze
    res_corr = client.post(
        "/api/admin/disruptions/analyze",
        json={"description": train_text, "corrected_location": "Feni"},
        auth=ADMIN_AUTH,
    )
    assert res_corr.status_code == 200
    data_corr = res_corr.json()
    assert data_corr["status"] == "READY"
    assert data_corr["extracted"]["location"] == "Feni"
    assert data_corr["extracted"]["transport_mode"] == "TRAIN"

    # 5. Ambiguous description requiring clarification
    vague_text = "An incident has occurred near Cumilla."
    res4 = client.post("/api/admin/disruptions/analyze", json={"description": vague_text}, auth=ADMIN_AUTH)
    assert res4.status_code == 200
    data4 = res4.json()
    assert data4["status"] == "NEEDS_CLARIFICATION"
    assert data4["clarification_message"] is not None
    assert data4["extracted"]["matching_status"] == "NEEDS CLARIFICATION"
    assert data4["total_affected_routes"] == 0


def test_simplified_publish_and_search_integration(client: TestClient):
    """
    Tests one-click simplified publish from description and asserts that dynamic
    route alerts attach only to routes traversing the affected railway section.
    """
    train_desc = "A railway accident near Cumilla has suspended train movement on the affected railway section."
    pub_res = client.post(
        "/api/admin/disruptions/publish-simplified",
        json={"description": train_desc, "source_name": "Bangladesh Railway"},
        auth=ADMIN_AUTH,
    )
    assert pub_res.status_code == 201
    dis_data = pub_res.json()
    dis_id = dis_data["disruption_id"]
    assert dis_data["status"] == "ACTIVE"
    assert dis_data["transport_mode"] == "TRAIN"

    try:
        # Search route Dhaka -> Noakhali (Upakul Express train traverses Cumilla)
        search_res = client.post("/api/search", json={"origin": "Dhaka", "destination": "Noakhali"})
        assert search_res.status_code == 200
        routes = search_res.json()["routes"]

        train_routes = [r for r in routes if r["kind"].upper() == "TRAIN"]
        bus_routes = [r for r in routes if r["kind"].upper() == "BUS"]

        assert len(train_routes) > 0
        for t_r in train_routes:
            assert t_r["is_affected"] is True
            assert any(a["disruption_id"] == dis_id for a in t_r["disruption_alerts"])

        # Bus routes through the same district must NOT be marked affected
        for b_r in bus_routes:
            assert b_r["is_affected"] is False
            assert len(b_r["disruption_alerts"]) == 0

        # Unrelated train routes (Dhaka -> Sylhet) must NOT be marked affected
        sylhet_res = client.post("/api/search", json={"origin": "Dhaka", "destination": "Sylhet"})
        assert sylhet_res.status_code == 200
        sylhet_trains = [r for r in sylhet_res.json()["routes"] if r["kind"].upper() == "TRAIN"]
        for t_r in sylhet_trains:
            assert t_r["is_affected"] is False
            assert len(t_r["disruption_alerts"]) == 0

    finally:
        client.delete(f"/api/admin/disruptions/{dis_id}", auth=ADMIN_AUTH)

    # 2. Test publishing with corrected_location override
    pub_corr = client.post(
        "/api/admin/disruptions/publish-simplified",
        json={
            "description": "Bus movement suspended due to severe protest on highway.",
            "corrected_location": "Gazipur",
            "source_name": "Traffic Police",
        },
        auth=ADMIN_AUTH,
    )
    assert pub_corr.status_code == 201
    corr_data = pub_corr.json()
    assert corr_data["location_name"] == "Gazipur"
    assert corr_data["transport_mode"] == "BUS"
    client.delete(f"/api/admin/disruptions/{corr_data['disruption_id']}", auth=ADMIN_AUTH)


def test_disruption_lifecycle_endpoints_and_audit_trail(client: TestClient):
    """
    Test A: Verifies all lifecycle action buttons and endpoints:
    - Deactivate (/deactivate and /inactive)
    - Resolve (/resolve and /resolved)
    - Cancel (/cancel and /cancelled)
    - Activate (/activate and /active)
    - Audit Trail (/audit-logs)
    - Delete (soft-delete / archive)
    And verifies public route alert reflection across statuses.
    """
    # 1. Create active disruption
    pub_res = client.post(
        "/api/admin/disruptions/publish-simplified",
        json={"description": "Train accident near Cumilla has blocked railway movement."},
        auth=ADMIN_AUTH,
    )
    assert pub_res.status_code == 201
    dis_id = pub_res.json()["disruption_id"]

    try:
        # Public search while ACTIVE -> must attach alert
        search_active = client.post("/api/search", json={"origin": "Dhaka", "destination": "Noakhali"})
        assert search_active.status_code == 200
        active_trains = [r for r in search_active.json()["routes"] if r["kind"].upper() == "TRAIN"]
        assert len(active_trains) > 0
        assert active_trains[0]["is_affected"] is True

        # 2. Deactivate via /deactivate (or /inactive)
        deact_res = client.post(f"/api/admin/disruptions/{dis_id}/deactivate", json={}, auth=ADMIN_AUTH)
        assert deact_res.status_code == 200
        assert deact_res.json()["status"] == "INACTIVE"

        # Public search while INACTIVE -> must NOT attach alert
        search_inactive = client.post("/api/search", json={"origin": "Dhaka", "destination": "Noakhali"})
        assert search_inactive.status_code == 200
        inactive_trains = [r for r in search_inactive.json()["routes"] if r["kind"].upper() == "TRAIN"]
        assert len(inactive_trains) > 0
        assert inactive_trains[0]["is_affected"] is False

        # Test alias endpoint /active
        act_res = client.post(f"/api/admin/disruptions/{dis_id}/active", json={}, auth=ADMIN_AUTH)
        assert act_res.status_code == 200
        assert act_res.json()["status"] == "ACTIVE"

        # Test alias endpoint /inactive
        inact_res = client.post(f"/api/admin/disruptions/{dis_id}/inactive", json={}, auth=ADMIN_AUTH)
        assert inact_res.status_code == 200
        assert inact_res.json()["status"] == "INACTIVE"

        # 3. Resolve via /resolve (or /resolved)
        res_res = client.post(f"/api/admin/disruptions/{dis_id}/resolve", json={}, auth=ADMIN_AUTH)
        assert res_res.status_code == 200
        assert res_res.json()["status"] == "RESOLVED"
        assert res_res.json()["resolved_at"] is not None

        # Public search while RESOLVED -> must NOT attach alert
        search_resolved = client.post("/api/search", json={"origin": "Dhaka", "destination": "Noakhali"})
        resolved_trains = [r for r in search_resolved.json()["routes"] if r["kind"].upper() == "TRAIN"]
        assert resolved_trains[0]["is_affected"] is False

        # 4. Cancel Alert via /cancel (or /cancelled)
        canc_res = client.post(f"/api/admin/disruptions/{dis_id}/cancel", json={}, auth=ADMIN_AUTH)
        assert canc_res.status_code == 200
        assert canc_res.json()["status"] == "CANCELLED"

        # Public search while CANCELLED -> must NOT attach alert
        search_cancelled = client.post("/api/search", json={"origin": "Dhaka", "destination": "Noakhali"})
        canc_trains = [r for r in search_cancelled.json()["routes"] if r["kind"].upper() == "TRAIN"]
        assert canc_trains[0]["is_affected"] is False

        # 5. Audit Trail verification
        audit_res = client.get(f"/api/admin/disruptions/{dis_id}/audit-logs", auth=ADMIN_AUTH)
        assert audit_res.status_code == 200
        logs = audit_res.json()
        assert len(logs) >= 5
        actions = [l["action"] for l in logs]
        assert "CREATED" in actions
        assert "DEACTIVATED" in actions
        assert "ACTIVATED" in actions
        assert "RESOLVED" in actions
        assert "CANCELLED" in actions
        for l in logs:
            assert l["admin_id"] is not None
            assert l["created_at"] is not None

        # 6. Soft Delete
        del_res = client.delete(f"/api/admin/disruptions/{dis_id}", auth=ADMIN_AUTH)
        assert del_res.status_code == 200

        # Disruption should be archived and not appear in default list
        list_res = client.get("/api/admin/disruptions", auth=ADMIN_AUTH)
        assert not any(d["disruption_id"] == dis_id for d in list_res.json())

    except Exception:
        client.delete(f"/api/admin/disruptions/{dis_id}", auth=ADMIN_AUTH)
        raise


def test_railway_disruption_stoppage_vs_corridor_transit_brahmanbaria(client: TestClient):
    """
    Test B: Comprehensive Railway Disruption Detection in Brahmanbaria:
    Verifies that:
    1. Trains stopping in Brahmanbaria (Group A: Bijoy Express 785/786, etc.) are detected with (Scheduled Stop).
    2. Trains passing through Brahmanbaria WITHOUT stopping (Group B: Sonar Bangla Express 787/788,
       Cox's Bazar Express 813/814, Suborna Express 701/702) are detected with (Non-Stop Transit).
    3. Both groups are combined without duplicates.
    4. Unrelated trains (Ekota Express, Silk City Express, Tista Express, Meghna Express) are EXCLUDED.
    5. When published, public search for Dhaka -> Chattogram (Sonar Bangla Express) attaches the disruption alert,
       while Dhaka -> Rajshahi and Chattogram -> Chandpur do NOT.
    """
    desc = "Brahmanbaria railway track is blocked due to an accident."

    # 1. Analyze preview
    analyze_res = client.post(
        "/api/admin/disruptions/analyze",
        json={"description": desc},
        auth=ADMIN_AUTH,
    )
    assert analyze_res.status_code == 200
    preview = analyze_res.json()
    assert preview["status"] == "READY"
    assert preview["extracted"]["location"] == "Brahmanbaria"
    assert preview["extracted"]["transport_mode"] == "TRAIN"

    affected_routes = preview["affected_routes"]
    services_detected = {r["service"] for r in affected_routes}
    matched_sections_by_svc = {r["service"]: r["matched_section"] for r in affected_routes}

    # Verify Group A: Bijoy Express stops in Brahmanbaria (at Akhaura)
    assert any("Bijoy Express" in s for s in services_detected)
    bijoy_svcs = [s for s in services_detected if "Bijoy Express" in s]
    for b_s in bijoy_svcs:
        assert "Scheduled Stop" in matched_sections_by_svc[b_s]

    # Verify Group B: Sonar Bangla Express passes through without stopping
    assert any("Sonar Bangla Express" in s for s in services_detected)
    sonar_svcs = [s for s in services_detected if "Sonar Bangla Express" in s]
    for s_s in sonar_svcs:
        assert "Non-Stop Transit" in matched_sections_by_svc[s_s]

    # Verify Group B: Cox's Bazar Express passes through without stopping
    assert any("Coxs Bazar Express" in s for s in services_detected)
    cox_svcs = [s for s in services_detected if "Coxs Bazar Express" in s]
    for c_s in cox_svcs:
        assert "Non-Stop Transit" in matched_sections_by_svc[c_s]

    # Verify Group B: Suborna Express passes through without stopping
    assert any("Suborna Express" in s for s in services_detected)
    suborna_svcs = [s for s in services_detected if "Suborna Express" in s]
    for su_s in suborna_svcs:
        assert "Non-Stop Transit" in matched_sections_by_svc[su_s]

    # Verify exclusions: Unrelated trains must NOT be included
    assert not any("Silk City" in s for s in services_detected)
    assert not any("Ekota" in s for s in services_detected)
    assert not any("Tista" in s for s in services_detected)
    assert not any("Sundarban" in s for s in services_detected)
    assert not any("Meghna" in s for s in services_detected)
    assert not any("Banalata" in s for s in services_detected)

    # Verify no duplicates
    assert len(services_detected) == len(affected_routes)

    # 2. Publish and test public route searches
    pub_res = client.post(
        "/api/admin/disruptions/publish-simplified",
        json={"description": desc},
        auth=ADMIN_AUTH,
    )
    assert pub_res.status_code == 201
    dis_id = pub_res.json()["disruption_id"]

    try:
        # Search Dhaka -> Chattogram: Sonar Bangla Express must be marked affected
        search_ctg = client.post("/api/search", json={"origin": "Dhaka", "destination": "Chattogram"})
        assert search_ctg.status_code == 200
        ctg_trains = [r for r in search_ctg.json()["routes"] if r["kind"].upper() == "TRAIN"]
        assert len(ctg_trains) > 0
        for t in ctg_trains:
            assert t["is_affected"] is True
            assert any(a["disruption_id"] == dis_id for a in t["disruption_alerts"])

        # Search Dhaka -> Rajshahi: Unrelated train routes must NOT be affected
        search_raj = client.post("/api/search", json={"origin": "Dhaka", "destination": "Rajshahi"})
        assert search_raj.status_code == 200
        raj_trains = [r for r in search_raj.json()["routes"] if r["kind"].upper() == "TRAIN"]
        for t in raj_trains:
            assert t["is_affected"] is False
            assert len(t["disruption_alerts"]) == 0

        # Search Chattogram -> Chandpur (Meghna Express): Unrelated train routes must NOT be affected
        search_chp = client.post("/api/search", json={"origin": "Chattogram", "destination": "Chandpur"})
        assert search_chp.status_code == 200
        chp_trains = [r for r in search_chp.json()["routes"] if r["kind"].upper() == "TRAIN"]
        for t in chp_trains:
            assert t["is_affected"] is False
            assert len(t["disruption_alerts"]) == 0

    finally:
        client.delete(f"/api/admin/disruptions/{dis_id}", auth=ADMIN_AUTH)


def test_district_spelling_variations_and_bengali(client: TestClient):
    """
    Test C: Verifies automatic location extraction with district spelling variations and Bengali script:
    - Brahmanbaria / ব্রাহ্মণবাড়িয়া
    - Comilla / Cumilla
    - Chittagong / Chattogram
    - Barisal / Barishal
    - Bogra / Bogura
    - Jessore / Jashore
    """
    test_cases = [
        ("ব্রাহ্মণবাড়িয়া railway track blocked due to an accident.", "Brahmanbaria", "TRAIN"),
        ("A train derailed near Comilla causing suspension.", "Cumilla", "TRAIN"),
        ("Road blockage in Chittagong affecting highway traffic.", "Chattogram", "BUS"),
        ("Heavy waterlogging in Barisal has halted buses.", "Barishal", "BUS"),
        ("Highway obstruction near Bogra causing delays.", "Bogura", "BUS"),
        ("Bus strike in Jessore district.", "Jashore", "BUS"),
    ]

    for desc, expected_district, expected_mode in test_cases:
        res = client.post(
            "/api/admin/disruptions/analyze",
            json={"description": desc},
            auth=ADMIN_AUTH,
        )
        assert res.status_code == 200, f"Failed for {desc}"
        data = res.json()
        assert data["status"] == "READY", f"Status not READY for {desc}: {data}"
        assert data["extracted"]["location"] == expected_district, f"Expected {expected_district}, got {data['extracted']['location']} for {desc}"
        assert data["extracted"]["transport_mode"] == expected_mode, f"Expected {expected_mode}, got {data['extracted']['transport_mode']} for {desc}"

