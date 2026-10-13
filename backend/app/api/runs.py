"""Ind-01: durable agent runs API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth.deps import get_current_identity
from ..runs import runs
from ..runs.service import execute_run, start_and_run
from ..runs.trace import classify_failure, list_spans

router = APIRouter(prefix="/api/runs", tags=["runs"])


class StartRunBody(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[dict[str, Any]] = Field(default_factory=list)
    session_id: str | None = None
    # Crash/pause drill: stop after N agent steps (after a tool_result), then resume.
    pause_after_steps: int | None = Field(default=None, ge=1)
    force_timeout: bool = False


class ResumeBody(BaseModel):
    pause_after_steps: int | None = Field(default=None, ge=1)
    force_timeout: bool = False


@router.get("")
def list_runs(
    identity: dict[str, Any] = Depends(get_current_identity),
) -> dict[str, Any]:
    items = runs.list(tenant_id=identity["tenant_id"])
    return {"count": len(items), "items": items}


@router.get("/{run_id}")
def get_run(
    run_id: str,
    identity: dict[str, Any] = Depends(get_current_identity),
) -> dict[str, Any]:
    rec = runs.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="run not found")
    if rec["tenant_id"] != identity["tenant_id"] and identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="跨租户不可读该 run")
    return rec


@router.post("")
async def post_run(
    body: StartRunBody,
    identity: dict[str, Any] = Depends(get_current_identity),
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


@router.post("/{run_id}/resume")
async def resume_run(
    run_id: str,
    body: ResumeBody | None = None,
    identity: dict[str, Any] = Depends(get_current_identity),
) -> dict[str, Any]:
    body = body or ResumeBody()
    rec = runs.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="run not found")
    if rec["tenant_id"] != identity["tenant_id"] and identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="跨租户不可 resume")
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


@router.get("/{run_id}/trace")
def get_run_trace(
    run_id: str,
    identity: dict[str, Any] = Depends(get_current_identity),
) -> dict[str, Any]:
    rec = runs.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="run not found")
    if rec["tenant_id"] != identity["tenant_id"] and identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="跨租户不可读 trace")
    spans = list_spans(run_id)
    return {
        "run_id": run_id,
        "status": rec["status"],
        "failure_mode": classify_failure(rec.get("steps") or [], rec["status"], rec.get("error") or ""),
        "span_count": len(spans),
        "spans": spans,
    }


@router.get("/{run_id}/replay")
def replay_run(
    run_id: str,
    identity: dict[str, Any] = Depends(get_current_identity),
) -> dict[str, Any]:
    """Trajectory replay: return recorded steps/spans without calling the LLM again."""
    rec = runs.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="run not found")
    if rec["tenant_id"] != identity["tenant_id"] and identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="跨租户不可 replay")
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
