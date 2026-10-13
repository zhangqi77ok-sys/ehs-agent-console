"""Chapter 1: EHS domain REST — hazards + CAPA (+ eng-3 auth deps)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth.deps import get_current_identity
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


def _require_write(identity: dict[str, Any]) -> None:
    if not identity.get("domain_write"):
        raise HTTPException(
            status_code=403,
            detail=f"角色「{identity['role']}」为只读，不能开单/推进",
        )


@router.get("/hazards")
def get_hazards(
    keyword: str = "",
    status: str = "",
    level: str = "",
    plant: str = "",
    category: str = "",
    overdue_only: bool = False,
    identity: dict[str, Any] = Depends(get_current_identity),
) -> dict[str, Any]:
    plant_f = plant or (identity.get("plant_filter") or "")
    return query_hazard_ledger(
        keyword=keyword,
        status=status,
        level=level,
        plant=plant_f,
        category=category,
        overdue_only=overdue_only,
    )


@router.get("/hazards/open")
def get_open_hazards(
    include_pending_verify: bool = True,
    identity: dict[str, Any] = Depends(get_current_identity),
) -> dict[str, Any]:
    data = list_open_hazards(include_pending_verify=include_pending_verify)
    plant = identity.get("plant_filter")
    if plant:
        items = [i for i in data["items"] if plant in str(i.get("plant") or "")]
        data = {**data, "items": items, "count": len(items), "tenant_plant_filter": plant}
    return data


@router.get("/tickets")
def get_tickets(
    hazard_id: str = "",
    status: str = "",
    identity: dict[str, Any] = Depends(get_current_identity),
) -> dict[str, Any]:
    _ = identity
    return list_corrective_tickets(hazard_id=hazard_id, status=status)


@router.post("/tickets")
def post_ticket(
    body: CreateTicketBody,
    identity: dict[str, Any] = Depends(get_current_identity),
) -> dict[str, Any]:
    _require_write(identity)
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
def post_advance(
    ticket_id: str,
    body: AdvanceTicketBody,
    identity: dict[str, Any] = Depends(get_current_identity),
) -> dict[str, Any]:
    _require_write(identity)
    result = advance_corrective_ticket(
        ticket_id=ticket_id,
        action=body.action,
        evidence_note=body.evidence_note,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "推进失败")
    return result


@router.get("/domain/summary")
def domain_summary(
    identity: dict[str, Any] = Depends(get_current_identity),
) -> dict[str, Any]:
    plant = identity.get("plant_filter") or ""
    all_h = query_hazard_ledger(plant=plant)
    open_h = list_open_hazards()
    if plant:
        open_items = [i for i in open_h["items"] if plant in str(i.get("plant") or "")]
        open_h = {**open_h, "items": open_items, "count": len(open_items)}
    overdue = query_hazard_ledger(overdue_only=True, plant=plant)
    tickets = list_corrective_tickets()
    return {
        "chapter": 1,
        "identity": identity,
        "as_of": all_h.get("as_of"),
        "hazard_total": all_h["count"],
        "open_count": open_h["count"],
        "overdue_count": overdue["count"],
        "ticket_count": tickets["count"],
        "hazards": all_h["items"],
        "tickets": tickets["items"],
    }
