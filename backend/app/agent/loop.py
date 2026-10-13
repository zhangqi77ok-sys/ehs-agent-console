"""Handwritten Agent loop — observe → decide → act → observe …"""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator, Callable
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.agent import llm
from app.agent.llm import LLMCallError, LLMConfigError
from app.config import settings
from app.tools.domain_tools import ToolContext
from app.tools.registry import WRITE_TOOLS, run_tool_async, schemas_for_tools

CheckpointCb = Callable[[dict[str, Any]], object]


def _checkpoint_payload(
    *,
    message: str,
    history: list[dict],
    tool_results: list[dict],
    steps: list[dict],
    budget_used: int,
) -> dict[str, Any]:
    return {
        "message": message,
        "history": list(history),
        "tool_results": list(tool_results),
        "steps": list(steps),
        "budget_used": budget_used,
        "next_index": budget_used,
    }


async def _emit(cb: CheckpointCb | None, payload: dict[str, Any]) -> None:
    if not cb:
        return
    maybe = cb(payload)
    if inspect.isawaitable(maybe):
        await maybe


async def stream_agent(
    message: str,
    session: Session,
    *,
    history: list[dict] | None = None,
    force_timeout: bool = False,
    tenant_id: str = "demo-plant",
    role: str = "ehs_engineer",
    actor: str = "",
    resume_state: dict[str, Any] | None = None,
    pause_after_steps: int | None = None,
    on_checkpoint: CheckpointCb | None = None,
    on_hitl: CheckpointCb | None = None,
    hitl_enabled: bool | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield events: identity, budget, step_start, tool_call, tool_result, note, final, paused, error, done."""
    identity = {
        "tenant_id": tenant_id,
        "role": role,
        "actor": actor or role,
    }
    ctx = ToolContext(
        session=session,
        tenant_id=tenant_id,
        role=role,
        actor=identity["actor"],
    )
    schemas = schemas_for_tools()
    use_hitl = settings.hitl_enabled if hitl_enabled is None else hitl_enabled

    rs = resume_state or {}
    steps: list[dict[str, Any]] = list(rs.get("steps") or [])
    tool_results: list[dict[str, Any]] = list(rs.get("tool_results") or [])
    hist = list(rs.get("history") if rs.get("history") is not None else (history or []))
    message = str(rs.get("message") or message)
    start_i = int(rs.get("budget_used") or rs.get("next_index") or 0)
    budget_max = settings.max_agent_steps
    budget_used = start_i

    yield {"event": "identity", "data": identity}
    yield {"event": "budget", "data": {"used": budget_used, "max": budget_max, "unit": "steps"}}

    if start_i > 0:
        note = {
            "index": start_i,
            "kind": "note",
            "note": "resumed_from_checkpoint",
            "detail": f"从 checkpoint 续跑，已完成步数 {start_i}/{budget_max}",
        }
        steps.append(note)
        yield {"event": "note", "data": note}

    if force_timeout and start_i == 0:
        drill = {
            "index": 0,
            "kind": "note",
            "note": "force_timeout_drill",
            "detail": "本轮启用强制超时练习。",
        }
        steps.append(drill)
        yield {"event": "note", "data": drill}

    for i in range(start_i, budget_max):
        budget_used = i + 1
        yield {"event": "step_start", "data": {"index": budget_used, "max": budget_max}}
        yield {
            "event": "budget",
            "data": {"used": budget_used, "max": budget_max, "unit": "steps"},
        }

        try:
            decision = await llm.complete(
                message,
                hist,
                tool_results,
                schemas,
                force_timeout=force_timeout and start_i == 0 and i == start_i,
            )
        except (LLMConfigError, LLMCallError) as exc:
            detail = str(exc)
            fail_step = {
                "index": budget_used,
                "kind": "final",
                "content": f"调用失败：{detail}",
            }
            steps.append(fail_step)
            yield {"event": "error", "data": {"detail": detail, "index": budget_used}}
            yield {"event": "final", "data": fail_step}
            ck = _checkpoint_payload(
                message=message,
                history=hist,
                tool_results=tool_results,
                steps=steps,
                budget_used=budget_used,
            )
            await _emit(
                on_checkpoint,
                {**ck, "_status": "failed", "_reply": fail_step["content"], "_error": detail},
            )
            yield {
                "event": "done",
                "data": {
                    "reply": fail_step["content"],
                    "steps": steps,
                    "budget": {"used": budget_used, "max": budget_max, "unit": "steps"},
                    "identity": identity,
                    "ok": False,
                    "status": "failed",
                },
            }
            return

        if decision.get("type") == "tool_call":
            name = str(decision.get("name") or "")
            args = dict(decision.get("arguments") or {})
            call_id = f"call_{uuid4().hex[:8]}"
            call_step = {
                "index": budget_used,
                "kind": "tool_call",
                "name": name,
                "arguments": args,
                "call_id": call_id,
            }
            steps.append(call_step)
            yield {"event": "tool_call", "data": call_step}

            # HITL gate for write tools (Ch5)
            if use_hitl and on_hitl and name in settings.hitl_write_tool_set:
                ck = _checkpoint_payload(
                    message=message,
                    history=hist,
                    tool_results=tool_results,
                    steps=steps,
                    budget_used=budget_used,
                )
                ck["pending_tool"] = {"name": name, "arguments": args, "call_id": call_id}
                await _emit(
                    on_hitl,
                    {
                        **ck,
                        "_status": "awaiting_approval",
                        "_reply": f"等待人工审批写工具：{name}",
                        "_hitl_tool": name,
                        "_hitl_arguments": args,
                        "_hitl_call_id": call_id,
                    },
                )
                yield {
                    "event": "paused",
                    "data": {
                        "status": "awaiting_approval",
                        "detail": f"等待人工审批写工具：{name}",
                        "steps": steps,
                        "budget": {"used": budget_used, "max": budget_max, "unit": "steps"},
                        "pending_tool": ck["pending_tool"],
                    },
                }
                yield {
                    "event": "done",
                    "data": {
                        "reply": f"等待人工审批写工具：{name}",
                        "steps": steps,
                        "budget": {"used": budget_used, "max": budget_max, "unit": "steps"},
                        "identity": identity,
                        "ok": True,
                        "status": "awaiting_approval",
                    },
                }
                return

            result = await run_tool_async(name, args, ctx)
            result_step = {
                "index": budget_used,
                "kind": "tool_result",
                "name": name,
                "result": result,
                "call_id": call_id,
            }
            steps.append(result_step)
            tool_results.append(
                {"name": name, "arguments": args, "result": result, "call_id": call_id}
            )
            yield {"event": "tool_result", "data": result_step}

            ck = _checkpoint_payload(
                message=message,
                history=hist,
                tool_results=tool_results,
                steps=steps,
                budget_used=budget_used,
            )
            await _emit(on_checkpoint, {**ck, "_status": "running", "_reply": ""})

            if pause_after_steps and budget_used >= pause_after_steps:
                await _emit(
                    on_checkpoint,
                    {**ck, "_status": "paused", "_reply": f"已按 pause_after_steps={pause_after_steps} 暂停"},
                )
                yield {
                    "event": "paused",
                    "data": {
                        "status": "paused",
                        "detail": f"已按 pause_after_steps={pause_after_steps} 暂停",
                        "steps": steps,
                        "budget": {"used": budget_used, "max": budget_max, "unit": "steps"},
                    },
                }
                yield {
                    "event": "done",
                    "data": {
                        "reply": f"已暂停（完成 {budget_used} 步）",
                        "steps": steps,
                        "budget": {"used": budget_used, "max": budget_max, "unit": "steps"},
                        "identity": identity,
                        "ok": True,
                        "status": "paused",
                    },
                }
                return
            continue

        # final
        content = str(decision.get("content") or "")
        final_step = {"index": budget_used, "kind": "final", "content": content}
        steps.append(final_step)
        yield {"event": "final", "data": final_step}
        ck = _checkpoint_payload(
            message=message,
            history=hist,
            tool_results=tool_results,
            steps=steps,
            budget_used=budget_used,
        )
        await _emit(on_checkpoint, {**ck, "_status": "completed", "_reply": content})
        yield {
            "event": "done",
            "data": {
                "reply": content,
                "steps": steps,
                "budget": {"used": budget_used, "max": budget_max, "unit": "steps"},
                "identity": identity,
                "ok": True,
                "status": "completed",
            },
        }
        return

    # budget exhausted
    content = f"已达最大步数 {budget_max}，请缩小问题或续跑。"
    final_step = {"index": budget_used, "kind": "final", "content": content}
    steps.append(final_step)
    yield {"event": "final", "data": final_step}
    ck = _checkpoint_payload(
        message=message,
        history=hist,
        tool_results=tool_results,
        steps=steps,
        budget_used=budget_used,
    )
    await _emit(
        on_checkpoint,
        {**ck, "_status": "failed", "_reply": content, "_error": "budget_exhausted"},
    )
    yield {
        "event": "done",
        "data": {
            "reply": content,
            "steps": steps,
            "budget": {"used": budget_used, "max": budget_max, "unit": "steps"},
            "identity": identity,
            "ok": False,
            "status": "failed",
        },
    }


async def run_agent(
    message: str,
    session: Session,
    **kwargs: Any,
) -> dict[str, Any]:
    reply = ""
    steps: list[dict] = []
    budget: dict[str, Any] = {"used": 0, "max": settings.max_agent_steps, "unit": "steps"}
    identity: dict[str, Any] = {}
    status = "completed"
    async for evt in stream_agent(message, session, **kwargs):
        name = evt["event"]
        data = evt["data"]
        if name in ("tool_call", "tool_result", "final", "note"):
            steps.append(data)
        if name == "final":
            reply = data.get("content") or ""
        if name == "budget":
            budget = data
        if name == "identity":
            identity = data
        if name == "error":
            reply = data.get("detail") or reply
            status = "failed"
        if name == "paused":
            status = data.get("status") or "paused"
            reply = data.get("detail") or reply
            steps = data.get("steps") or steps
            budget = data.get("budget") or budget
        if name == "done":
            reply = data.get("reply") or reply
            budget = data.get("budget") or budget
            steps = data.get("steps") or steps
            identity = data.get("identity") or identity
            status = data.get("status") or status
            if data.get("ok") is False and status == "completed":
                status = "failed"
    return {
        "reply": reply,
        "steps": steps,
        "budget": budget,
        "identity": identity,
        "status": status,
    }
