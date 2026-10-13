def test_list_hazards_seeded(client, eng_headers):
    r = client.get("/api/hazards", headers=eng_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 4
    assert all(h["tenant_id"] == "demo-plant" for h in data)


def test_create_ticket_and_advance_happy_path(client, eng_headers):
    r = client.post(
        "/api/tickets",
        headers=eng_headers,
        json={"hazard_id": "HZ-2026-001", "measures": "更换过期灭火器并复核压力表"},
    )
    assert r.status_code == 201, r.text
    ticket = r.json()
    tid = ticket["ticket_id"]
    assert ticket["status"] == "待执行"

    r = client.post(
        f"/api/tickets/{tid}/advance",
        headers=eng_headers,
        json={"action": "start"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "执行中"

    r = client.post(
        f"/api/tickets/{tid}/advance",
        headers=eng_headers,
        json={"action": "submit_verify"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "待验收"

    r = client.post(
        f"/api/tickets/{tid}/advance",
        headers=eng_headers,
        json={"action": "close", "evidence_note": "现场照片+压力表回绿，已张贴新铭牌"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "已关闭"
    assert r.json()["evidence_note"]

    hz = client.get("/api/hazards/HZ-2026-001", headers=eng_headers).json()
    assert hz["status"] == "已闭环"


def test_illegal_transition_400(client, eng_headers):
    r = client.post(
        "/api/tickets",
        headers=eng_headers,
        json={"hazard_id": "HZ-2026-002", "measures": "紧固接地线"},
    )
    tid = r.json()["ticket_id"]
    r = client.post(
        f"/api/tickets/{tid}/advance",
        headers=eng_headers,
        json={"action": "close", "evidence_note": "不应该成功"},
    )
    assert r.status_code == 400
    assert "不允许" in r.json()["detail"] or "期望" in r.json()["detail"]


def test_close_without_evidence_400(client, eng_headers):
    r = client.post(
        "/api/tickets",
        headers=eng_headers,
        json={"hazard_id": "HZ-2026-003", "measures": "补装反光镜"},
    )
    tid = r.json()["ticket_id"]
    client.post(f"/api/tickets/{tid}/advance", headers=eng_headers, json={"action": "start"})
    client.post(
        f"/api/tickets/{tid}/advance",
        headers=eng_headers,
        json={"action": "submit_verify"},
    )
    r = client.post(
        f"/api/tickets/{tid}/advance",
        headers=eng_headers,
        json={"action": "close", "evidence_note": "  "},
    )
    assert r.status_code == 400
    assert "证据" in r.json()["detail"]


def test_cross_tenant_cannot_see_or_write(client, eng_headers, other_tenant_headers):
    # demo engineer creates on HZ-2026-001
    r = client.post(
        "/api/tickets",
        headers=eng_headers,
        json={"hazard_id": "HZ-2026-001", "measures": "demo措施"},
    )
    assert r.status_code == 201
    tid = r.json()["ticket_id"]

    # other tenant cannot list demo hazards
    r = client.get("/api/hazards", headers=other_tenant_headers)
    assert r.status_code == 200
    assert all(h["id"] != "HZ-2026-001" for h in r.json())

    # other tenant cannot advance demo ticket
    r = client.post(
        f"/api/tickets/{tid}/advance",
        headers=other_tenant_headers,
        json={"action": "start"},
    )
    assert r.status_code == 404
