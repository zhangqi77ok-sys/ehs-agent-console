"""Ind-03: HITL approval gate for write tools."""

from __future__ import annotations

import pytest


@pytest.fixture
def mock_llm(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    from app.config import settings

    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "hitl_enabled", True)


def test_write_tool_awaits_approval_then_approve(client, mock_llm):
    headers = {"X-Role": "ehs_engineer", "X-Tenant-Id": "default"}
    # HZ-2026-001 + 开单 → create_corrective_ticket
    started = client.post(
        "/api/runs",
        headers=headers,
        json={"message": "给 HZ-2026-001 开整改单，措施：更换灭火器并点检"},
    )
    assert started.status_code == 200, started.text
    body = started.json()
    assert body["status"] == "awaiting_approval"
    pending = body.get("pending_approvals") or []
    assert pending, body
    ap_id = pending[0]["approval_id"]

    decided = client.post(
        f"/api/approvals/{ap_id}/decide",
        headers=headers,
        json={"approve": True, "note": "同意开单"},
    )
    assert decided.status_code == 200, decided.text
    run = decided.json()["run"]
    assert run["status"] == "completed"
    assert run.get("reply") or (run.get("agent") or {}).get("reply")


def test_viewer_cannot_decide(client, mock_llm):
    headers = {"X-Role": "ehs_engineer", "X-Tenant-Id": "default"}
    started = client.post(
        "/api/runs",
        headers=headers,
        json={"message": "给 HZ-2026-009 开整改单，措施：加防倾倒链"},
    )
    assert started.status_code == 200
    ap_id = (started.json().get("pending_approvals") or [{}])[0].get("approval_id")
    assert ap_id
    denied = client.post(
        f"/api/approvals/{ap_id}/decide",
        headers={"X-Role": "viewer", "X-Tenant-Id": "default"},
        json={"approve": True},
    )
    assert denied.status_code == 403


def test_health_hitl(client, mock_llm):
    assert client.get("/health").json().get("hitl") is True
