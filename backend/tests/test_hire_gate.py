"""主管过关门禁：关键路径一破就红（CI 可直接跑）。

这是技术过关清单的自动化底座，不是录用保证。
"""

from __future__ import annotations

import re

from app.auth.refresh_store import reset_revocations


def test_hire_gate_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_hire_gate_evidence_required_close(client, eng_headers):
    created = client.post(
        "/api/tickets",
        headers=eng_headers,
        json={"hazard_id": "HZ-2026-003", "measures": "清理堆放", "owner": "eng-1"},
    )
    assert created.status_code in (200, 201), created.text
    tid = created.json()["ticket_id"]
    assert client.post(
        f"/api/tickets/{tid}/advance", headers=eng_headers, json={"action": "start"}
    ).status_code == 200
    assert client.post(
        f"/api/tickets/{tid}/advance",
        headers=eng_headers,
        json={"action": "submit_verify"},
    ).status_code == 200
    bad = client.post(
        f"/api/tickets/{tid}/advance",
        headers=eng_headers,
        json={"action": "close", "evidence_note": ""},
    )
    assert bad.status_code == 400
    assert "证据" in bad.json()["detail"]


def test_hire_gate_viewer_denied_write(client, viewer_headers):
    r = client.post(
        "/api/tickets",
        headers=viewer_headers,
        json={"hazard_id": "HZ-2026-001", "measures": "x", "owner": "v"},
    )
    assert r.status_code == 403


def test_hire_gate_jwt_mint_refresh_logout(client):
    reset_revocations()
    minted = client.post(
        "/auth/token",
        json={"tenant_id": "demo-plant", "role": "ehs_engineer", "actor": "gate-eng"},
    )
    assert minted.status_code == 200, minted.text
    body = minted.json()
    assert body["access_token"]
    assert body.get("refresh_token")
    access = body["access_token"]
    refresh = body["refresh_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["actor"] == "gate-eng"

    # refresh must not work as access
    bad = client.get("/auth/me", headers={"Authorization": f"Bearer {refresh}"})
    assert bad.status_code == 401

    refreshed = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert refreshed.status_code == 200, refreshed.text
    new_access = refreshed.json()["access_token"]
    new_refresh = refreshed.json()["refresh_token"]
    assert new_access
    me2 = client.get("/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me2.status_code == 200

    # old refresh rotated away
    old_refresh_again = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert old_refresh_again.status_code == 401

    logged_out = client.post("/auth/logout", json={"refresh_token": new_refresh})
    assert logged_out.status_code == 200
    assert logged_out.json().get("ok") is True
    after = client.post("/auth/refresh", json={"refresh_token": new_refresh})
    assert after.status_code == 401


def test_hire_gate_traceparent_roundtrip(client):
    inbound = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    r = client.get("/health", headers={"traceparent": inbound})
    assert r.status_code == 200
    out = r.headers.get("traceparent") or ""
    assert out.startswith("00-4bf92f3577b34da6a3ce929d0e0e4736-")
    assert re.match(
        r"^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$",
        out,
        re.I,
    )
    assert r.headers.get("X-Request-Id")


def test_hire_gate_traceparent_generated(client):
    r = client.get("/health")
    assert r.status_code == 200
    tp = r.headers.get("traceparent") or ""
    assert re.match(r"^00-[0-9a-f]{32}-[0-9a-f]{16}-01$", tp, re.I)


def test_hire_gate_rag_tenant_scoped(client, eng_headers, other_tenant_headers):
    from app.db import session as session_mod
    from app.rag.store import reset_regulations_store
    from app.tools.domain_tools import ToolContext, search_regulations

    reset_regulations_store()  # reload with tenant corpora
    db = session_mod.SessionLocal()
    try:
        demo = search_regulations(
            ToolContext(session=db, tenant_id="demo-plant", role="ehs_engineer", actor="eng"),
            query="灭火器过期",
            top_k=5,
        )
        assert demo["ok"] is True
        assert demo["result"]["count"] >= 1
        assert all(h.get("tenant_id") == "demo-plant" for h in demo["result"]["hits"])

        other = search_regulations(
            ToolContext(session=db, tenant_id="other-plant", role="ehs_engineer", actor="o"),
            query="蓝色安全帽反光条",
            top_k=5,
        )
        assert other["ok"] is True
        assert other["result"]["count"] >= 1
        assert all(h.get("tenant_id") == "other-plant" for h in other["result"]["hits"])

        # other-plant must not see demo-only fire extinguisher corpus as mixed tenant ids
        leak = search_regulations(
            ToolContext(session=db, tenant_id="other-plant", role="ehs_engineer", actor="o"),
            query="灭火器压力表",
            top_k=5,
        )
        assert leak["ok"] is True
        for h in leak["result"]["hits"]:
            assert h.get("tenant_id") == "other-plant"
    finally:
        db.close()


def test_hire_gate_agent_loop_importable():
    from app.agent.loop import run_agent  # noqa: F401

    assert callable(run_agent)


def test_hire_gate_eval_deterministic_subset():
    """Import eval runner / cases — deterministic suite must be present."""
    from pathlib import Path
    import json

    cases = Path(__file__).resolve().parents[1] / "eval" / "cases.json"
    assert cases.exists(), "eval/cases.json missing"
    data = json.loads(cases.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) >= 1
