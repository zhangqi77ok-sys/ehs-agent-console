"""Ind-02: span trace + recorded trajectory replay."""

from __future__ import annotations

import pytest


@pytest.fixture
def mock_llm(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    from app.config import settings

    monkeypatch.setattr(settings, "llm_provider", "mock")


def test_run_produces_trace_and_replay(client, mock_llm):
    headers = {"X-Role": "ehs_engineer", "X-Tenant-Id": "default"}
    started = client.post(
        "/api/runs",
        headers=headers,
        json={"message": "有哪些未闭环隐患？"},
    )
    assert started.status_code == 200, started.text
    run_id = started.json()["run_id"]
    assert started.json().get("span_count", 0) >= 1

    trace = client.get(f"/api/runs/{run_id}/trace", headers=headers)
    assert trace.status_code == 200
    body = trace.json()
    assert body["span_count"] >= 2
    kinds = {s["kind"] for s in body["spans"]}
    assert "run" in kinds
    assert body["failure_mode"] == "ok"

    replay = client.get(f"/api/runs/{run_id}/replay", headers=headers)
    assert replay.status_code == 200
    rb = replay.json()
    assert rb["mode"] == "recorded_trajectory"
    assert rb["steps"]
    assert rb["reply"]


def test_health_agent_trace(client, mock_llm):
    assert client.get("/health").json().get("agent_trace") is True
