"""Execute / resume durable agent runs."""

from __future__ import annotations

from typing import Any

from ..agent.loop import run_agent
from ..config import settings
from .store import runs
from .trace import classify_failure, replace_spans_from_steps


def _strip_meta(ck: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in ck.items() if not str(k).startswith("_")}


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
    if rec["status"] not in {"pending", "paused", "running", "failed"} and not resume:
        if rec["status"] == "completed":
            return rec

    resume_state = None
    if resume or rec["status"] == "paused":
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
    )
    # Final status already written by on_checkpoint; refresh
    final = runs.get(run_id) or {}
    if result.get("status") == "paused" and final.get("status") != "paused":
        runs.save_checkpoint(
            run_id,
            status="paused",
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
    return {
        **final,
        "failure_mode": failure_mode,
        "span_count": len(spans),
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
