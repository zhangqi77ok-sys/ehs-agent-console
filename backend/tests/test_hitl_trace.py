"""Ch5: HITL write-tool gate + span trace/replay."""


def test_hitl_gates_create_ticket(client, eng_headers, monkeypatch):
    monkeypatch.setenv("HITL_ENABLED", "true")
    # reload settings
    from app.config import Settings
    import app.config as config_mod

    config_mod.settings = Settings(
        database_url=config_mod.settings.database_url,
        llm_provider="mock",
        hitl_enabled=True,
    )

    r = client.post(
        "/api/runs",
        headers=eng_headers,
        json={
            "message": "给 HZ-2026-002 开整改单，措施：紧固接地线并测电阻",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "awaiting_approval", body
    pending = body.get("pending_approvals") or []
    assert pending, body
    ap_id = pending[0]["approval_id"]

    # approve + continue
    d = client.post(
        f"/api/approvals/{ap_id}/decide",
        headers=eng_headers,
        json={"approve": True, "note": "同意开单"},
    )
    assert d.status_code == 200, d.text
    run = d.json()["run"]
    assert run["status"] == "completed"
    assert "TK-" in (run.get("reply") or "") or "整改单" in (run.get("reply") or "")

    # trace
    tr = client.get(f"/api/runs/{run['run_id']}/trace", headers=eng_headers)
    assert tr.status_code == 200
    assert tr.json()["span_count"] >= 1

    rp = client.get(f"/api/runs/{run['run_id']}/replay", headers=eng_headers)
    assert rp.status_code == 200
    assert rp.json()["mode"] == "recorded_trajectory"


def test_hitl_reject(client, eng_headers, monkeypatch):
    from app.config import Settings
    import app.config as config_mod

    config_mod.settings = Settings(
        database_url=config_mod.settings.database_url,
        llm_provider="mock",
        hitl_enabled=True,
    )
    r = client.post(
        "/api/runs",
        headers=eng_headers,
        json={"message": "给 HZ-2026-004 开整改单，措施：重做标识"},
    )
    assert r.json()["status"] == "awaiting_approval"
    ap_id = r.json()["pending_approvals"][0]["approval_id"]
    d = client.post(
        f"/api/approvals/{ap_id}/decide",
        headers=eng_headers,
        json={"approve": False, "note": "暂缓"},
    )
    assert d.status_code == 200
    run = d.json()["run"]
    assert run["status"] == "completed"
    assert "驳回" in (run.get("reply") or "") or "失败" in (run.get("reply") or "")
