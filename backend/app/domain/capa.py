"""CAPA (整改单) state machine — pure functions, no I/O."""

from __future__ import annotations

# action -> (from_status, to_status)
TRANSITIONS: dict[str, tuple[str, str]] = {
    "start": ("待执行", "执行中"),
    "submit_verify": ("执行中", "待验收"),
    "close": ("待验收", "已关闭"),
    "reject": ("待验收", "执行中"),
}

# hazard status side-effects when ticket advances
HAZARD_STATUS_ON_TICKET: dict[str, str] = {
    "start": "整改中",
    "submit_verify": "待验收",
    "close": "已闭环",
    "reject": "整改中",
}


def transition(status: str, action: str) -> tuple[str, str | None]:
    """Return (new_status, error). On illegal moves, new_status stays unchanged."""
    rule = TRANSITIONS.get(action)
    if rule is None:
        return status, f"未知动作: {action}"
    expected_from, to_status = rule
    if status != expected_from:
        return status, f"不允许从「{status}」执行「{action}」，期望状态「{expected_from}」"
    return to_status, None


def require_evidence_for_close(action: str, evidence_note: str | None) -> str | None:
    """Return error message if close lacks non-empty evidence; else None."""
    if action != "close":
        return None
    if evidence_note is None or not str(evidence_note).strip():
        return "关闭整改单必须提供非空验收证据（evidence_note）"
    return None


def hazard_status_for_action(action: str) -> str | None:
    return HAZARD_STATUS_ON_TICKET.get(action)
