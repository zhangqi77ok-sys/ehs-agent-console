"""Ch4/Ch5: durable runs, trace/replay, HITL approvals."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.deps import get_identity
from app.auth.tenant import domain_can_write
from app.config import settings
from app.runs import approvals as approvals_store
from app.runs.service import decide_and_continue, execute_run, start_and_run
from app.runs.store import runs
from app.runs.trace import classify_failure, list_spans

router = APIRouter(prefix="/api", tags=["runs"])


class StartRunBody(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[dict[str, Any]] = Field(default_factory=list)
    session_id: str | None = None
    pause_after_steps: int | None = Field(default=None, ge=1)
    force_timeout: bool = False


class ResumeBody(BaseModel):
    pause_after_steps: int | None = Field(default=None, ge=1)
    force_timeout: bool = False


class DecideBody(BaseModel):
    approve: bool = True
    note: str = ""


def _guard_run(rec: dict[str, Any], identity: dict[str, Any]) -> None:
    if rec["tenant_id"] != identity["tenant_id"] and identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="跨租户不可操作该 run")


@router.get("/runs")
def list_runs(identity: dict[str, Any] = Depends(get_identity)) -> dict[str, Any]:
    items = runs.list(tenant_id=identity["tenant_id"])
    return {"count": len(items), "items": items, "hitl_enabled": settings.hitl_enabled}


@router.get("/runs/{run_id}")
def get_run(run_id: str, identity: dict[str, Any] = Depends(get_identity)) -> dict[str, Any]:
    rec = runs.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="run not found")
    _guard_run(rec, identity)
    pending = approvals_store.list_approvals(run_id=run_id, status="pending")
    return {**rec, "pending_approvals": pending}


@router.post("/runs")
async def post_run(
    body: StartRunBody,
    identity: dict[str, Any] = Depends(get_identity),
) -> dict[str, Any]:
    try:
        return await start_and_run(
            message=body.message,
            tenant_id=identity["tenant_id"],
            role=identity["role"],
            session_id=body.session_id,
            history=body.history,
            pause_after_steps=body.pause_after_steps,
            force_timeout=body.force_timeout,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/runs/{run_id}/resume")
async def resume_run(
    run_id: str,
    body: ResumeBody | None = None,
    identity: dict[str, Any] = Depends(get_identity),
) -> dict[str, Any]:
    body = body or ResumeBody()
    rec = runs.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="run not found")
    _guard_run(rec, identity)
    try:
        return await execute_run(
            run_id,
            resume=True,
            pause_after_steps=body.pause_after_steps,
            force_timeout=body.force_timeout,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/runs/{run_id}/trace")
def get_run_trace(run_id: str, identity: dict[str, Any] = Depends(get_identity)) -> dict[str, Any]:
    rec = runs.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="run not found")
    _guard_run(rec, identity)
    spans = list_spans(run_id)
    return {
        "run_id": run_id,
        "status": rec["status"],
        "failure_mode": classify_failure(rec.get("steps") or [], rec["status"], rec.get("error") or ""),
        "span_count": len(spans),
        "spans": spans,
    }


@router.get("/runs/{run_id}/replay")
def replay_run(run_id: str, identity: dict[str, Any] = Depends(get_identity)) -> dict[str, Any]:
    rec = runs.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="run not found")
    _guard_run(rec, identity)
    spans = list_spans(run_id)
    return {
        "run_id": run_id,
        "mode": "recorded_trajectory",
        "status": rec["status"],
        "message": rec["message"],
        "reply": rec.get("reply"),
        "steps": rec.get("steps") or [],
        "spans": spans,
        "checkpoint": rec.get("checkpoint") or {},
        "note": "回放不重新调用 LLM；用于排障与评测对照。",
    }


@router.get("/approvals")
def list_pending_approvals(
    status: str = "pending",
    identity: dict[str, Any] = Depends(get_identity),
) -> dict[str, Any]:
    items = approvals_store.list_approvals(status=status or None)
    out = []
    for a in items:
        rec = runs.get(a["run_id"])
        if not rec:
            continue
        if rec["tenant_id"] == identity["tenant_id"] or identity.get("role") == "admin":
            out.append({**a, "run_status": rec["status"], "run_message": rec["message"]})
    return {"count": len(out), "items": out, "hitl_enabled": settings.hitl_enabled}


@router.post("/approvals/{approval_id}/decide")
async def decide_approval(
    approval_id: str,
    body: DecideBody,
    identity: dict[str, Any] = Depends(get_identity),
) -> dict[str, Any]:
    ap = approvals_store.get_approval(approval_id)
    if not ap:
        raise HTTPException(status_code=404, detail="approval not found")
    rec = runs.get(ap["run_id"])
    if not rec:
        raise HTTPException(status_code=404, detail="run not found")
    _guard_run(rec, identity)
    if not domain_can_write(identity["role"]):
        raise HTTPException(status_code=403, detail="只读角色不能审批写操作")
    try:
        return await decide_and_continue(
            approval_id,
            approve=body.approve,
            decided_by=identity.get("actor") or identity.get("role") or "operator",
            note=body.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
