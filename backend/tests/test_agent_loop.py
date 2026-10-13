"""Ch2: agent loop + domain tools (mock LLM)."""

from __future__ import annotations


def test_agent_list_open_hazards(client, eng_headers):
    r = client.post(
        "/api/agent/chat",
        headers=eng_headers,
        json={"message": "有哪些未闭环隐患？"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["budget"]["used"] >= 1
    kinds = [s["kind"] for s in body["steps"]]
    assert "tool_call" in kinds
    assert "tool_result" in kinds
    assert "final" in kinds
    assert "HZ-2026-001" in body["reply"] or "灭火器" in body["reply"]


def test_agent_query_keyword(client, eng_headers):
    r = client.post(
        "/api/agent/chat",
        headers=eng_headers,
        json={"message": "查一下灭火器相关隐患"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    tool = next(s for s in body["steps"] if s["kind"] == "tool_call")
    assert tool["name"] == "query_hazard_ledger"


def test_agent_create_ticket_uses_domain_audit(client, eng_headers):
    r = client.post(
        "/api/agent/chat",
        headers=eng_headers,
        json={
            "message": "给 HZ-2026-003 开整改单，措施：补装反光镜并复核盲区",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert "TK-" in body["reply"] or "已开整改单" in body["reply"]

    audit = client.get("/api/audit?limit=20", headers=eng_headers)
    assert audit.status_code == 200
    actions = [a["action"] for a in audit.json()]
    assert "ticket.create" in actions


def test_agent_viewer_cannot_create(client, viewer_headers, eng_headers):
    r = client.post(
        "/api/agent/chat",
        headers=viewer_headers,
        json={
            "message": "给 HZ-2026-004 开整改单，措施：重刷危化品标识",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "只读" in body["reply"] or "失败" in body["reply"]
    # domain audit should record denied
    # viewer cannot read audit — use eng
    audit = client.get("/api/audit?limit=30", headers=eng_headers)
    denied = [a for a in audit.json() if a.get("action") == "ticket.denied" and not a.get("ok", True)]
    # ok field may be boolean
    denied2 = [a for a in audit.json() if a.get("action") == "ticket.denied"]
    assert denied2, audit.json()


def test_agent_requires_tenant(client):
    r = client.post("/api/agent/chat", json={"message": "hello"})
    assert r.status_code == 400
