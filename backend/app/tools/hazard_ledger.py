"""EHS hazard ledger facade — backed by SQLAlchemy repository (eng-1 persistence)."""

from __future__ import annotations

from typing import Any

from ..db import repo


def query_hazard_ledger(
    keyword: str = "",
    status: str = "",
    level: str = "",
    plant: str = "",
    category: str = "",
    overdue_only: bool = False,
) -> dict[str, Any]:
    return repo.query_hazard_ledger(
        keyword=keyword,
        status=status,
        level=level,
        plant=plant,
        category=category,
        overdue_only=overdue_only,
    )


def list_open_hazards(include_pending_verify: bool = True) -> dict[str, Any]:
    return repo.list_open_hazards(include_pending_verify=include_pending_verify)


def create_corrective_ticket(
    hazard_id: str,
    action: str = "",
    measures: str = "",
    assignee: str = "",
    owner: str = "",
    due_days: int = 7,
) -> dict[str, Any]:
    return repo.create_corrective_ticket(
        hazard_id=hazard_id,
        action=action,
        measures=measures,
        assignee=assignee,
        owner=owner,
        due_days=due_days,
    )


def list_corrective_tickets(hazard_id: str = "", status: str = "") -> dict[str, Any]:
    return repo.list_corrective_tickets(hazard_id=hazard_id, status=status)


def advance_corrective_ticket(
    ticket_id: str, action: str, evidence_note: str = ""
) -> dict[str, Any]:
    return repo.advance_corrective_ticket(
        ticket_id=ticket_id, action=action, evidence_note=evidence_note
    )


def list_tickets() -> list[dict[str, Any]]:
    return repo.list_tickets()
