"""Ch11: Supervisor multi-agent routing."""

from __future__ import annotations

from app.agent.supervisor import route_intent


def test_route_intent_read_vs_write():
    assert route_intent("有哪些未闭环隐患？") == "investigator"
    assert route_intent("查制度：灭火器过期怎么处理") == "investigator"
    assert route_intent("给 HZ-2026-001 开整改单，措施：更换灭火器") == "clerk"
    assert route_intent("关闭 TK-2026-001，说明：验收通过") == "clerk"


def test_supervisor_investigator_read(client, eng_headers, monkeypatch):
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
        json={"message": "有哪些待整改的隐患？请列出未闭环的。", "multi_agent": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["supervisor"]["route"] == "investigator"
    tools = [s.get("name") for s in body["steps"] if s.get("kind") == "tool_call"]
    assert "list_open_hazards" in tools
    assert all(s.get("agent") in {None, "investigator", "supervisor"} or s.get("kind") == "note" for s in body["steps"])
    agents = {s.get("agent") for s in body["steps"] if s.get("kind") == "tool_call"}
    assert agents == {"investigator"}


def test_supervisor_clerk_write(client, eng_headers, monkeypatch):
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
            "message": "给 HZ-2026-003 开整改单，措施：补装反光镜并现场复核",
            "multi_agent": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["supervisor"]["route"] == "clerk"
    tools = [s.get("name") for s in body["steps"] if s.get("kind") == "tool_call"]
    assert "create_corrective_ticket" in tools
    agents = {s.get("agent") for s in body["steps"] if s.get("kind") == "tool_call"}
    assert agents == {"clerk"}


def test_investigator_cannot_run_write_tool_directly(client, eng_headers, monkeypatch):
    """Even if somehow write tool chosen, allowlist blocks under investigator."""
    from app.tools.domain_tools import ToolContext
    from app.tools.registry import run_tool
    import app.db.session as session_mod

    db = session_mod.SessionLocal()
    try:
        ctx = ToolContext(session=db, tenant_id="demo-plant", role="ehs_engineer", actor="t")
        out = run_tool(
            "create_corrective_ticket",
            {"hazard_id": "HZ-2026-001", "measures": "x"},
            ctx,
            allowed={"query_hazard_ledger"},
        )
        assert out["ok"] is False
        assert out.get("denied") is True
    finally:
        db.close()


def test_supervisor_handoff_dual_timeline(client, eng_headers, monkeypatch):
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
    assert body["supervisor"].get("handoff") is True
    agents = {s.get("agent") for s in body["steps"]}
    assert "investigator" in agents
    assert "clerk" in agents
    assert "supervisor" in agents
    tools = [s.get("name") for s in body["steps"] if s.get("kind") == "tool_call"]
    assert any(t in tools for t in ("query_hazard_ledger", "list_open_hazards"))
    assert "create_corrective_ticket" in tools
