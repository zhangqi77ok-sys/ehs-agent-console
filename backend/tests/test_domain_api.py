"""Domain REST + header ACL — no LLM required."""

from __future__ import annotations


def test_health_reports_sqlalchemy(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["persistence"] == "sqlalchemy"
    assert body["hazard_count"] >= 12


def test_list_hazards(client):
    r = client.get("/api/hazards", headers={"X-Role": "ehs_engineer"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 12
    assert any(h["id"] == "HZ-2026-001" for h in body["items"])


def test_viewer_cannot_create_ticket(client):
    r = client.post(
        "/api/tickets",
        headers={"X-Role": "viewer", "X-Tenant-Id": "default"},
        json={"hazard_id": "HZ-2026-001", "measures": "只读角色不应成功", "owner": "x"},
    )
    assert r.status_code == 403


def test_engineer_create_and_advance(client):
    headers = {"X-Role": "ehs_engineer", "X-Tenant-Id": "default"}
    created = client.post(
        "/api/tickets",
        headers=headers,
        json={
            "hazard_id": "HZ-2026-001",
            "measures": "更换灭火器并点检",
            "owner": "张三",
            "due_days": 3,
        },
    )
    assert created.status_code == 200
    tid = created.json()["ticket"]["ticket_id"]

    started = client.post(
        f"/api/tickets/{tid}/advance",
        headers=headers,
        json={"action": "start"},
    )
    assert started.status_code == 200
    assert started.json()["ticket"]["status"] == "执行中"


def test_plant_a_tenant_filters_hazards(client):
    r = client.get(
        "/api/hazards",
        headers={"X-Tenant-Id": "plant_a", "X-Role": "viewer"},
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert items
    assert all("一号车间" in (h.get("plant") or "") for h in items)


def test_domain_summary_includes_identity(client):
    r = client.get(
        "/api/domain/summary",
        headers={"X-Tenant-Id": "hq", "X-Role": "admin"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["identity"]["role"] == "admin"
    assert body["identity"]["tenant_id"] == "hq"
    assert body["hazard_total"] >= 12


def test_sessions_persist(client):
    created = client.post("/api/sessions", json={"tenant_id": "default", "role": "viewer"})
    assert created.status_code == 200
    sid = created.json()["session_id"]
    got = client.get(f"/api/sessions/{sid}")
    assert got.status_code == 200
    assert got.json()["session_id"] == sid
