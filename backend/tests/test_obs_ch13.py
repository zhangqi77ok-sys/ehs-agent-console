"""Ch13 observability summary + span export."""

from __future__ import annotations


def test_obs_summary_emptyish(client, eng_headers):
    r = client.get("/api/obs/summary", headers=eng_headers)
    assert r.status_code == 200
    data = r.json()
    assert "run_count" in data
    assert "hitl_pending" in data
    assert "tool_deny_rate" in data
    assert "avg_steps" in data
    assert "failure_modes" in data


def test_metrics_text(client, eng_headers):
    r = client.get("/metrics", headers=eng_headers)
    assert r.status_code == 200
    assert "ehs_hitl_pending" in r.text
    assert "ehs_tool_deny_rate" in r.text


def test_spans_export_after_run(client, eng_headers, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    from app.config import Settings
    import app.config as config_mod

    config_mod.settings = Settings(
        database_url=str(config_mod.settings.database_url),
        llm_provider="mock",
        hitl_enabled=False,
    )
    started = client.post(
        "/api/runs",
        headers=eng_headers,
        json={"message": "查一下灭火器相关隐患"},
    )
    assert started.status_code == 200, started.text
    run_id = started.json()["run_id"]
    exp = client.get(f"/api/runs/{run_id}/spans/export", headers=eng_headers)
    assert exp.status_code == 200
    assert "attachment" in exp.headers.get("content-disposition", "")
    body = exp.json()
    assert body["run_id"] == run_id
    assert "failure_mode" in body
    assert "spans" in body
