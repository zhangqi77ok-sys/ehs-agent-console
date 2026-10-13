"""Ch4: durable runs with pause/resume checkpoint."""


def test_run_pause_and_resume(client, eng_headers):
    r = client.post(
        "/api/runs",
        headers=eng_headers,
        json={"message": "有哪些未闭环隐患？", "pause_after_steps": 1},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "paused"
    assert body["budget_used"] >= 1
    run_id = body["run_id"]
    assert body["checkpoint"].get("tool_results") or body["steps"]

    r2 = client.post(f"/api/runs/{run_id}/resume", headers=eng_headers, json={})
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert body2["status"] == "completed"
    assert body2["reply"]


def test_list_runs_tenant_scoped(client, eng_headers, other_tenant_headers):
    client.post(
        "/api/runs",
        headers=eng_headers,
        json={"message": "查灭火器"},
    )
    mine = client.get("/api/runs", headers=eng_headers).json()
    other = client.get("/api/runs", headers=other_tenant_headers).json()
    assert mine["count"] >= 1
    assert other["count"] == 0
