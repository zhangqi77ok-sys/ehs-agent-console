"""CAPA ticket state machine — domain rules interviewers ask about."""

from __future__ import annotations

from app.db import repo


def test_happy_path_create_start_submit_close(repo_fresh):
    created = repo.create_corrective_ticket(
        hazard_id="HZ-2026-001",
        measures="更换灭火器并完成点检张贴",
        owner="张三",
        due_days=5,
    )
    assert created["ok"] is True
    tid = created["ticket"]["ticket_id"]
    assert created["ticket"]["status"] == "待执行"
    assert created["hazard"]["status"] == "整改中"

    started = repo.advance_corrective_ticket(ticket_id=tid, action="start")
    assert started["ok"] is True
    assert started["ticket"]["status"] == "执行中"

    submitted = repo.advance_corrective_ticket(
        ticket_id=tid, action="submit_verify", evidence_note="已更换并拍照"
    )
    assert submitted["ok"] is True
    assert submitted["ticket"]["status"] == "待验收"
    assert submitted["hazard"]["status"] == "待验收"

    closed = repo.advance_corrective_ticket(
        ticket_id=tid, action="close", evidence_note="现场复核通过"
    )
    assert closed["ok"] is True
    assert closed["ticket"]["status"] == "已关闭"
    assert closed["hazard"]["status"] == "已闭环"
    assert closed["hazard"].get("closed_at")


def test_reject_returns_to_in_progress(repo_fresh):
    # CA-102 is seeded as 待验收
    rejected = repo.advance_corrective_ticket(
        ticket_id="CA-102", action="reject", evidence_note="台账仍缺一页"
    )
    assert rejected["ok"] is True
    assert rejected["ticket"]["status"] == "执行中"
    assert rejected["hazard"]["status"] == "整改中"
    assert "驳回" in (rejected["ticket"].get("evidence_note") or "")


def test_illegal_transition_blocked(repo_fresh):
    # CA-101 is 执行中 — cannot close directly
    bad = repo.advance_corrective_ticket(ticket_id="CA-101", action="close", evidence_note="x")
    assert bad["ok"] is False
    assert "仅允许从" in bad["error"]


def test_cannot_open_second_active_ticket(repo_fresh):
    # HZ-2026-002 already has CA-101 active
    again = repo.create_corrective_ticket(
        hazard_id="HZ-2026-002", measures="重复开单应失败"
    )
    assert again["ok"] is False
    assert "未关闭整改单" in again["error"]


def test_closed_hazard_cannot_open_ticket(repo_fresh):
    bad = repo.create_corrective_ticket(
        hazard_id="HZ-2026-003", measures="已闭环不应开单"
    )
    assert bad["ok"] is False
    assert "已闭环" in bad["error"]


def test_close_requires_evidence(repo_fresh):
    # CA-102 is 待验收 but wipe evidence path: use ticket with empty evidence
    # Seed CA-102 has evidence — create fresh path from HZ-2026-009
    created = repo.create_corrective_ticket(
        hazard_id="HZ-2026-009", measures="加防倾倒链", owner="张三"
    )
    tid = created["ticket"]["ticket_id"]
    repo.advance_corrective_ticket(ticket_id=tid, action="start")
    repo.advance_corrective_ticket(ticket_id=tid, action="submit_verify")  # no evidence_note
    # clear evidence by advancing only — ticket may have empty evidence_note
    ticket = next(
        t for t in repo.list_corrective_tickets(hazard_id="HZ-2026-009")["items"] if t["ticket_id"] == tid
    )
    if not ticket.get("evidence_note"):
        closed = repo.advance_corrective_ticket(ticket_id=tid, action="close")
        assert closed["ok"] is False
        assert "验收说明" in closed["error"]
