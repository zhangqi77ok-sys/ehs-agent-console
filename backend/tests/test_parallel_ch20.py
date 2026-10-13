"""Ch20: parallel Investigator + Clerk fan-out."""

from __future__ import annotations

from app.agent.supervisor import needs_parallel_fanout, route_intent


def test_needs_parallel_fanout_detection():
    assert needs_parallel_fanout("同时查灭火器制度，并给 HZ-2026-001 起草整改单措施：更换过期灭火器") is True
    assert needs_parallel_fanout("查制度：灭火器过期怎么处理，并起草整改措施草案") is True
    assert needs_parallel_fanout("并行查隐患列表并开整改单，措施：补装反光镜") is True
    # sequential handoff, not parallel
    assert needs_parallel_fanout("先查灭火器隐患，再给 HZ-2026-001 开整改单，措施：更换过期灭火器") is False
    assert needs_parallel_fanout("有哪些未闭环隐患？") is False


def test_supervisor_parallel_path(client, eng_headers, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    from app.config import Settings
    import app.config as config_mod

    config_mod.settings = Settings(
        database_url=config_mod.settings.database_url,
        llm_provider="mock",
        hitl_enabled=False,
    )
    r = client.post(
        "/api/agent/chat",
        headers=eng_headers,
        json={
            "message": "同时查灭火器相关制度，并给 HZ-2026-001 开整改单，措施：更换过期灭火器",
            "multi_agent": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["supervisor"].get("parallel") is True
    assert body["supervisor"]["route"] == "parallel"
    agents = {s.get("agent") for s in body["steps"]}
    assert "investigator" in agents
    assert "clerk" in agents
    assert "supervisor" in agents
    notes = [s for s in body["steps"] if s.get("note") == "parallel_join"]
    assert notes, "expected parallel_join note"
    tools = [s.get("name") for s in body["steps"] if s.get("kind") == "tool_call"]
    # investigator should have used a read tool; clerk a write
    assert any(t in tools for t in ("search_regulations", "query_hazard_ledger", "list_open_hazards"))
    assert "create_corrective_ticket" in tools
    assert "【Investigator】" in (body.get("reply") or "") or "【Clerk】" in (body.get("reply") or "")


def test_handoff_not_flagged_parallel(client, eng_headers, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    from app.config import Settings
    import app.config as config_mod

    config_mod.settings = Settings(
        database_url=config_mod.settings.database_url,
        llm_provider="mock",
        hitl_enabled=False,
    )
    r = client.post(
        "/api/agent/chat",
        headers=eng_headers,
        json={
            "message": "先查灭火器隐患，再给 HZ-2026-001 开整改单，措施：更换过期灭火器",
            "multi_agent": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["supervisor"].get("parallel") is not True
    assert body["supervisor"].get("handoff") is True
