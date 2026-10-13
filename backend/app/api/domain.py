from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import Identity, deny_if_readonly
from app.db import repo
from app.db.models import Hazard, Ticket
from app.db.session import get_db

router = APIRouter(prefix="/api", tags=["domain"])


class HazardOut(BaseModel):
    id: str
    tenant_id: str
    title: str
    description: str
    plant: str
    area: str
    category: str
    level: str
    status: str
    owner: str
    deadline: date | None
    discoverer: str
    discovered_at: datetime | None
    closed_at: datetime | None
    risk_note: str | None

    model_config = {"from_attributes": True}


class TicketOut(BaseModel):
    ticket_id: str
    hazard_id: str
    tenant_id: str
    measures: str
    owner: str
    due_date: date | None
    status: str
    evidence_note: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class CreateTicketIn(BaseModel):
    hazard_id: str
    measures: str = Field(min_length=1)
    owner: str | None = None
    due_days: int | None = 7


class AdvanceIn(BaseModel):
    action: str
    evidence_note: str | None = None


def _hazard_out(h: Hazard) -> HazardOut:
    return HazardOut.model_validate(h)


def _ticket_out(t: Ticket) -> TicketOut:
    return TicketOut.model_validate(t)


@router.get("/hazards", response_model=list[HazardOut])
def get_hazards(
    identity: Identity,
    db: Annotated[Session, Depends(get_db)],
    status: str | None = None,
    level: str | None = None,
    plant: str | None = None,
    keyword: str | None = None,
):
    rows = repo.list_hazards(
        db,
        identity["tenant_id"],
        status=status,
        level=level,
        plant=plant,
        keyword=keyword,
    )
    return [_hazard_out(h) for h in rows]


@router.get("/hazards/{hazard_id}", response_model=HazardOut)
def get_hazard_detail(
    hazard_id: str,
    identity: Identity,
    db: Annotated[Session, Depends(get_db)],
):
    h = repo.get_hazard(db, identity["tenant_id"], hazard_id)
    if h is None:
        raise HTTPException(status_code=404, detail="隐患不存在")
    return _hazard_out(h)


@router.get("/tickets", response_model=list[TicketOut])
def get_tickets(
    identity: Identity,
    db: Annotated[Session, Depends(get_db)],
    hazard_id: str | None = None,
    status: str | None = None,
):
    rows = repo.list_tickets(
        db, identity["tenant_id"], hazard_id=hazard_id, status=status
    )
    return [_ticket_out(t) for t in rows]


@router.post("/tickets", response_model=TicketOut, status_code=201)
def post_ticket(
    body: CreateTicketIn,
    identity: Identity,
    db: Annotated[Session, Depends(get_db)],
):
    deny_if_readonly(
        db, identity, action="ticket.create", target_type="hazard", target_id=body.hazard_id
    )
    ticket, err = repo.create_ticket(
        db,
        tenant_id=identity["tenant_id"],
        role=identity["role"],
        actor=identity["actor"],
        hazard_id=body.hazard_id,
        measures=body.measures,
        owner=body.owner,
        due_days=body.due_days,
    )
    if err:
        if "不存在" in err:
            raise HTTPException(status_code=404, detail=err)
        raise HTTPException(status_code=400, detail=err)
    return _ticket_out(ticket)


@router.post("/tickets/{ticket_id}/advance", response_model=TicketOut)
def post_advance(
    ticket_id: str,
    body: AdvanceIn,
    identity: Identity,
    db: Annotated[Session, Depends(get_db)],
):
    deny_if_readonly(
        db, identity, action=body.action, target_type="ticket", target_id=ticket_id
    )
    ticket, err, code = repo.advance_ticket(
        db,
        tenant_id=identity["tenant_id"],
        role=identity["role"],
        actor=identity["actor"],
        ticket_id=ticket_id,
        action=body.action,
        evidence_note=body.evidence_note,
    )
    if err:
        raise HTTPException(status_code=code, detail=err)
    return _ticket_out(ticket)
