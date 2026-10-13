"""Ch15 MCP-style adapter."""

from __future__ import annotations


def test_mcp_tools_list(client, eng_headers):
    r = client.get("/api/mcp/tools", headers=eng_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 5
    names = {t["name"] for t in data["tools"]}
    assert "query_hazard_ledger" in names
    assert "create_corrective_ticket" in names
    sample = data["tools"][0]
    assert "inputSchema" in sample
    assert data["protocol"] == "mcp-compatible-thin"


def test_mcp_call_read_tool(client, eng_headers):
    r = client.post(
        "/api/mcp/call",
        headers=eng_headers,
        json={"name": "list_open_hazards", "arguments": {}},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["isError"] is False
    assert data["structured"]["ok"] is True


def test_mcp_call_viewer_denied(client):
    headers = {
        "X-Tenant-Id": "demo-plant",
        "X-Role": "viewer",
        "X-Actor": "v1",
    }
    r = client.post(
        "/api/mcp/call",
        headers=headers,
        json={
            "name": "create_corrective_ticket",
            "arguments": {"hazard_id": "HZ-2026-003", "measures": "x"},
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    assert data.get("denied") is True
