"""Ind-01: durable run checkpoint / pause / resume (mock LLM, no network)."""

from __future__ import annotations

import pytest


@pytest.fixture
def mock_llm(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    from app.config import settings

    monkeypatch.setattr(settings, "llm_provider", "mock")


def test_health_flags_durable_runs(client, mock_llm):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("durable_runs") is True


def test_pause_then_resume_completes(client, mock_llm):
    headers = {"X-Role": "ehs_engineer", "X-Tenant-Id": "default"}
    # Mock path: "未闭环" → list_open_hazards then final. pause after 1 step = after tool.
    started = client.post(
        "/api/runs",
        headers=headers,
        json={
            "message": "有哪些未闭环隐患？",
            "pause_after_steps": 1,
        },
    )
    assert started.status_code == 200, started.text
    body = started.json()
    assert body["status"] == "paused"
    run_id = body["run_id"]
    assert body["budget_used"] >= 1
    assert body.get("checkpoint", {}).get("tool_results")

    # Simulate process death: only DB state remains
    resumed = client.post(f"/api/runs/{run_id}/resume", headers=headers, json={})
    assert resumed.status_code == 200, resumed.text
    done = resumed.json()
    assert done["status"] == "completed"
    assert done.get("reply") or (done.get("agent") or {}).get("reply")
    # resumed note should appear in steps
    steps = done.get("steps") or []
    notes = [s for s in steps if s.get("note") == "resumed_from_checkpoint"]
    assert notes, steps


def test_get_run_tenant_isolation(client, mock_llm):
    headers = {"X-API-Key": "demo-plant-a"}
    started = client.post(
        "/api/runs",
        headers=headers,
        json={"message": "有哪些未闭环隐患？"},
    )
    assert started.status_code == 200
    run_id = started.json()["run_id"]

    denied = client.get(run_id and f"/api/runs/{run_id}", headers={"X-API-Key": "demo-plant-b"})
    assert denied.status_code == 403


def test_list_runs(client, mock_llm):
    headers = {"X-Role": "ehs_engineer", "X-Tenant-Id": "default"}
    client.post("/api/runs", headers=headers, json={"message": "有哪些未闭环隐患？"})
    listed = client.get("/api/runs", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["count"] >= 1
