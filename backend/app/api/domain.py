"""Chapter 1: EHS domain REST — hazards + CAPA, no Agent required."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..tools.hazard_ledger import (
    advance_corrective_ticket,
    create_corrective_ticket,
    list_corrective_tickets,
    list_open_hazards,
    query_hazard_ledger,
)

router = APIRouter(prefix="/api", tags=["domain"])


class CreateTicketBody(BaseModel):
    hazard_id: str
    measures: str = Field(..., min_length=1)
    owner: str = ""
    due_days: int = 7


class AdvanceTicketBody(BaseModel):
    action: str = Field(..., description="start | submit_verify | close | reject")
    evidence_note: str = ""


@router.get("/hazards")
def get_hazards(
    keyword: str = "",
    status: str = "",
    level: str = "",
    plant: str = "",
    category: str = "",
    overdue_only: bool = False,
) -> dict[str, Any]:
    return query_hazard_ledger(
        keyword=keyword,
        status=status,
        level=level,
        plant=plant,
        category=category,
        overdue_only=overdue_only,
    )


@router.get("/hazards/open")
def get_open_hazards(include_pending_verify: bool = True) -> dict[str, Any]:
    return list_open_hazards(include_pending_verify=include_pending_verify)


@router.get("/tickets")
def get_tickets(hazard_id: str = "", status: str = "") -> dict[str, Any]:
    return list_corrective_tickets(hazard_id=hazard_id, status=status)


@router.post("/tickets")
def post_ticket(body: CreateTicketBody) -> dict[str, Any]:
    result = create_corrective_ticket(
        hazard_id=body.hazard_id,
        measures=body.measures,
        owner=body.owner,
        due_days=body.due_days,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "开单失败")
    return result


@router.post("/tickets/{ticket_id}/advance")
def post_advance(ticket_id: str, body: AdvanceTicketBody) -> dict[str, Any]:
    result = advance_corrective_ticket(
        ticket_id=ticket_id,
        action=body.action,
        evidence_note=body.evidence_note,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "推进失败")
    return result


@router.get("/domain/summary")
def domain_summary() -> dict[str, Any]:
    """One-shot snapshot for the Chapter-1 console."""
    all_h = query_hazard_ledger()
    open_h = list_open_hazards()
    overdue = query_hazard_ledger(overdue_only=True)
    tickets = list_corrective_tickets()
    return {
        "chapter": 1,
        "as_of": all_h.get("as_of"),
        "hazard_total": all_h["count"],
        "open_count": open_h["count"],
        "overdue_count": overdue["count"],
        "ticket_count": tickets["count"],
        "hazards": all_h["items"],
        "tickets": tickets["items"],
    }
