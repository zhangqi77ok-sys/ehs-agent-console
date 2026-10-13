"""Execute / resume durable agent runs (+ HITL)."""

from __future__ import annotations

from typing import Any

from ..agent.loop import run_agent
from ..auth.tenant import assert_tool_allowed
from ..config import settings
from ..tools.registry import run_tool_async
from . import approvals as approvals_store
from .store import runs
from .trace import classify_failure, replace_spans_from_steps


def _strip_meta(ck: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in ck.items() if not str(k).startswith("_")}


async def _apply_pending_tool(run_id: str, *, approve: bool, note: str = "") -> dict[str, Any]:
    """Execute or deny the pending write tool, mutate checkpoint, then ready for resume."""
    rec = runs.get(run_id)
    if not rec:
        raise KeyError(run_id)
    ck = dict(rec.get("checkpoint") or {})
    pending = ck.get("pending_tool") or {}
    name = pending.get("name")
    args = pending.get("arguments") or {}
    call_id = pending.get("call_id") or ""
    if not name:
        raise ValueError("无 pending_tool，无法完成审批")

    steps = list(ck.get("steps") or rec.get("steps") or [])
    tool_results = list(ck.get("tool_results") or [])

    if approve:
        ok_tool, deny_reason = assert_tool_allowed(rec["role"], name)
        if not ok_tool:
            result = {"ok": False, "error": deny_reason, "denied": True}
        else:
            result = await run_tool_async(name, args)
    else:
        result = {
            "ok": False,
            "error": note or "人工驳回写操作",
            "denied": True,
            "hitl_rejected": True,
        }

    result_step = {
        "index": int(ck.get("budget_used") or rec.get("budget_used") or 0),
        "kind": "tool_result",
        "name": name,
        "result": result,
        "note": "hitl_approved" if approve else "hitl_rejected",
    }
    steps.append(result_step)
    tool_results.append(
        {"name": name, "arguments": args, "result": result, "call_id": call_id}
    )
    ck["steps"] = steps
    ck["tool_results"] = tool_results
    ck.pop("pending_tool", None)
    runs.save_checkpoint(
        run_id,
        status="paused",  # ready to resume loop
        checkpoint=ck,
        steps=steps,
        budget_used=int(ck.get("budget_used") or 0),
        reply="HITL 已处理，继续执行" if approve else "HITL 已驳回，继续执行",
    )
    return runs.get(run_id) or {}


async def execute_run(
    run_id: str,
    *,
    resume: bool = False,
    pause_after_steps: int | None = None,
    force_timeout: bool = False,
    history: list[dict] | None = None,
) -> dict[str, Any]:
    rec = runs.get(run_id)
    if not rec:
        raise KeyError(run_id)
    if rec["status"] == "completed" and resume:
        raise ValueError("run 已完成，无法 resume")
    if rec["status"] == "awaiting_approval" and resume:
        raise ValueError("run 等待 HITL 审批，请先调用 /api/approvals/{id}/decide")

    resume_state = None
    if resume or rec["status"] in {"paused"}:
        resume_state = _strip_meta(rec.get("checkpoint") or {})
        if not resume_state.get("message"):
            resume_state["message"] = rec["message"]

    async def on_checkpoint(payload: dict[str, Any]) -> None:
        status = str(payload.get("_status") or "running")
        reply = str(payload.get("_reply") or "")
        error = str(payload.get("_error") or "")
        ck = _strip_meta(payload)
        runs.save_checkpoint(
            run_id,
            status=status,
            checkpoint=ck,
            steps=list(ck.get("steps") or []),
            budget_used=int(ck.get("budget_used") or 0),
            reply=reply,
            error=error,
        )

    async def on_hitl(payload: dict[str, Any]) -> None:
        tool = str(payload.get("_hitl_tool") or "")
        args = payload.get("_hitl_arguments") or {}
        call_id = str(payload.get("_hitl_call_id") or "")
        ap = approvals_store.create_approval(
            run_id=run_id, tool_name=tool, arguments=args, call_id=call_id
        )
        ck = _strip_meta(payload)
        ck["pending_approval_id"] = ap["approval_id"]
        runs.save_checkpoint(
            run_id,
            status="awaiting_approval",
            checkpoint=ck,
            steps=list(ck.get("steps") or []),
            budget_used=int(ck.get("budget_used") or 0),
            reply=str(payload.get("_reply") or ""),
        )

    runs.save_checkpoint(
        run_id,
        status="running",
        checkpoint=_strip_meta(rec.get("checkpoint") or {"message": rec["message"]}),
        steps=list(rec.get("steps") or []),
        budget_used=int(rec.get("budget_used") or 0),
    )

    result = await run_agent(
        rec["message"],
        history=history,
        force_timeout=force_timeout,
        tenant_id=rec["tenant_id"],
        role=rec["role"],
        resume_state=resume_state,
        pause_after_steps=pause_after_steps,
        on_checkpoint=on_checkpoint,
        on_hitl=on_hitl if settings.hitl_enabled else None,
    )
    final = runs.get(run_id) or {}
    if result.get("status") in {"paused", "awaiting_approval"} and final.get("status") == "running":
        runs.save_checkpoint(
            run_id,
            status=str(result.get("status")),
            checkpoint=final.get("checkpoint") or {},
            steps=result.get("steps") or [],
            budget_used=int((result.get("budget") or {}).get("used") or 0),
            reply=result.get("reply") or "",
        )
        final = runs.get(run_id) or final

    steps = result.get("steps") or final.get("steps") or []
    spans = replace_spans_from_steps(run_id, steps)
    failure_mode = classify_failure(
        steps, str(final.get("status") or result.get("status") or ""), str(final.get("error") or "")
    )
    pending = approvals_store.list_approvals(run_id=run_id, status="pending")
    return {
        **final,
        "failure_mode": failure_mode,
        "span_count": len(spans),
        "pending_approvals": pending,
        "agent": {
            "reply": result.get("reply"),
            "steps": result.get("steps"),
            "budget": result.get("budget"),
            "identity": result.get("identity"),
            "status": result.get("status"),
        },
    }


async def start_and_run(
    *,
    message: str,
    tenant_id: str,
    role: str,
    session_id: str | None = None,
    history: list[dict] | None = None,
    pause_after_steps: int | None = None,
    force_timeout: bool = False,
) -> dict[str, Any]:
    created = runs.create(
        message=message,
        tenant_id=tenant_id,
        role=role,
        session_id=session_id,
        budget_max=settings.max_agent_steps,
        history=history,
    )
    return await execute_run(
        created["run_id"],
        resume=False,
        pause_after_steps=pause_after_steps,
        force_timeout=force_timeout,
        history=history,
    )


async def decide_and_continue(
    approval_id: str,
    *,
    approve: bool,
    decided_by: str = "",
    note: str = "",
) -> dict[str, Any]:
    ap = approvals_store.get_approval(approval_id)
    if not ap:
        raise KeyError(approval_id)
    if ap["status"] != "pending":
        raise ValueError(f"审批已处理：{ap['status']}")
    decided = approvals_store.decide_approval(
        approval_id, approve=approve, decided_by=decided_by, note=note
    )
    await _apply_pending_tool(ap["run_id"], approve=approve, note=note)
    # continue agent loop
    continued = await execute_run(ap["run_id"], resume=True)
    return {"approval": decided, "run": continued}
