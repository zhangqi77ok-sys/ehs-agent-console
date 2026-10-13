def test_viewer_post_ticket_403_and_audited(client, viewer_headers, eng_headers):
    before = client.get("/api/audit", headers=eng_headers)
    assert before.status_code == 200
    n0 = len(before.json())

    r = client.post(
        "/api/tickets",
        headers=viewer_headers,
        json={"hazard_id": "HZ-2026-001", "measures": "viewer 不应成功"},
    )
    assert r.status_code == 403

    after = client.get("/api/audit", headers=eng_headers).json()
    assert len(after) >= n0 + 1
    denied = [a for a in after if a["action"] == "ticket.denied" and a["ok"] is False]
    assert denied, after
    assert any("只读" in (a.get("error") or "") for a in denied)


def test_viewer_cannot_read_audit(client, viewer_headers):
    r = client.get("/api/audit", headers=viewer_headers)
    assert r.status_code == 403


def test_successful_close_grows_audit_with_evidence_flag(client, eng_headers):
    n0 = len(client.get("/api/audit", headers=eng_headers).json())
    r = client.post(
        "/api/tickets",
        headers=eng_headers,
        json={"hazard_id": "HZ-2026-004", "measures": "重做危化品标签"},
    )
    tid = r.json()["ticket_id"]
    client.post(f"/api/tickets/{tid}/advance", headers=eng_headers, json={"action": "start"})
    client.post(
        f"/api/tickets/{tid}/advance",
        headers=eng_headers,
        json={"action": "submit_verify"},
    )
    client.post(
        f"/api/tickets/{tid}/advance",
        headers=eng_headers,
        json={"action": "close", "evidence_note": "标签已更新并拍照存档"},
    )
    events = client.get("/api/audit", headers=eng_headers).json()
    assert len(events) > n0
    advances = [e for e in events if e["action"] == "ticket.advance" and e["ok"]]
    assert any(e["payload"].get("evidence_provided") is True for e in advances)


def test_close_denied_writes_audit(client, eng_headers):
    r = client.post(
        "/api/tickets",
        headers=eng_headers,
        json={"hazard_id": "HZ-2026-001", "measures": "措施A"},
    )
    tid = r.json()["ticket_id"]
    client.post(f"/api/tickets/{tid}/advance", headers=eng_headers, json={"action": "start"})
    client.post(
        f"/api/tickets/{tid}/advance",
        headers=eng_headers,
        json={"action": "submit_verify"},
    )
    r = client.post(
        f"/api/tickets/{tid}/advance",
        headers=eng_headers,
        json={"action": "close"},
    )
    assert r.status_code == 400
    events = client.get("/api/audit", headers=eng_headers).json()
    denied = [e for e in events if e["action"] == "ticket.denied" and e["ok"] is False]
    assert any("证据" in (e.get("error") or "") for e in denied)
