"""Handwritten Agent loop — observe → decide → act → observe … (+ Ind-01 checkpoint)."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any, AsyncIterator
from uuid import uuid4

from ..auth.tenant import assert_tool_allowed, resolve_identity
from ..config import settings
from ..tools.registry import schemas_for_tools, run_tool_async
from . import llm
from .llm import LLMCallError, LLMConfigError

CheckpointCb = Callable[[dict[str, Any]], object]


def _filter_schemas(allowed: set[str] | list[str]) -> list[dict[str, Any]]:
    allow = set(allowed)
    return schemas_for_tools(allow)


def _inject_tenant_args(name: str, args: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    out = dict(args or {})
    plant = identity.get("plant_filter")
    if plant and name in {"query_hazard_ledger", "list_open_hazards"}:
        if name == "query_hazard_ledger" and not out.get("plant"):
            out["plant"] = plant
    return out


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


async def _emit_checkpoint(cb: CheckpointCb | None, payload: dict[str, Any]) -> None:
    if not cb:
        return
    maybe = cb(payload)
    if inspect.isawaitable(maybe):
        await maybe


async def run_agent(
    message: str,
    history: list[dict] | None = None,
    force_timeout: bool = False,
    tenant_id: str = "default",
    role: str = "ehs_engineer",
    resume_state: dict[str, Any] | None = None,
    pause_after_steps: int | None = None,
    on_checkpoint: CheckpointCb | None = None,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    reply = ""
    budget: dict[str, Any] = {"used": 0, "max": settings.max_agent_steps, "unit": "steps"}
    identity: dict[str, Any] = {}
    status = "completed"
    async for evt in stream_agent(
        message,
        history,
        force_timeout=force_timeout,
        tenant_id=tenant_id,
        role=role,
        resume_state=resume_state,
        pause_after_steps=pause_after_steps,
        on_checkpoint=on_checkpoint,
    ):
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
            status = "paused"
            reply = data.get("detail") or reply
            steps = data.get("steps") or steps
            budget = data.get("budget") or budget
        if name == "done":
            reply = data.get("reply") or reply
            budget = data.get("budget") or budget
            steps = data.get("steps") or steps
            identity = data.get("identity") or identity
            if data.get("ok") is False:
                status = "failed"
            elif status != "paused":
                status = "completed"
    return {
        "reply": reply,
        "steps": steps,
        "budget": budget,
        "identity": identity,
        "status": status,
    }


async def stream_agent(
    message: str,
    history: list[dict] | None = None,
    force_timeout: bool = False,
    tenant_id: str = "default",
    role: str = "ehs_engineer",
    resume_state: dict[str, Any] | None = None,
    pause_after_steps: int | None = None,
    on_checkpoint: CheckpointCb | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield SSE events. Supports Ind-01 resume_state + pause_after_steps + on_checkpoint."""
    identity = resolve_identity(tenant_id, role)
    allowed = set(identity["allowed_tools"])
    schemas = _filter_schemas(allowed)

    rs = resume_state or {}
    steps: list[dict[str, Any]] = list(rs.get("steps") or [])
    tool_results: list[dict[str, Any]] = list(rs.get("tool_results") or [])
    hist = list(rs.get("history") if rs.get("history") is not None else (history or []))
    message = str(rs.get("message") or message)
    start_i = int(rs.get("budget_used") or rs.get("next_index") or 0)
    budget_max = settings.max_agent_steps
    budget_used = start_i

    yield {"event": "identity", "data": identity}
    yield {
        "event": "budget",
        "data": {"used": budget_used, "max": budget_max, "unit": "steps"},
    }
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
            "detail": "本轮启用强制超时练习：LLM HTTP 超时约 0.05s，仍走真实网关路径。",
        }
        steps.append(drill)
        yield {"event": "note", "data": drill}

    for i in range(start_i, budget_max):
        budget_used = i + 1
        yield {
            "event": "step_start",
            "data": {"index": budget_used, "max": budget_max},
        }
        yield {
            "event": "budget",
            "data": {"used": budget_used, "max": budget_max, "unit": "steps"},
        }

        note_q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async def on_retry(attempt: int, max_attempts: int, reason: str) -> None:
            await note_q.put(
                {
                    "index": budget_used,
                    "kind": "note",
                    "note": "llm_retry",
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "reason": reason,
                }
            )

        decision_task = asyncio.create_task(
            llm.complete(
                message,
                hist,
                tool_results,
                schemas,
                on_retry=on_retry,
                force_timeout=force_timeout,
            )
        )

        while not decision_task.done():
            try:
                note = await asyncio.wait_for(note_q.get(), timeout=0.15)
            except asyncio.TimeoutError:
                continue
            steps.append(note)
            yield {"event": "note", "data": note}

        while not note_q.empty():
            note = note_q.get_nowait()
            steps.append(note)
            yield {"event": "note", "data": note}

        try:
            decision = decision_task.result()
        except (LLMConfigError, LLMCallError) as exc:
            detail = str(exc)
            err = {"detail": detail, "index": budget_used}
            yield {"event": "error", "data": err}
            fail_step = {
                "index": budget_used,
                "kind": "final",
                "content": f"调用失败：{detail}",
            }
            steps.append(fail_step)
            yield {"event": "final", "data": fail_step}
            ck = _checkpoint_payload(
                message=message,
                history=hist,
                tool_results=tool_results,
                steps=steps,
                budget_used=budget_used,
            )
            await _emit_checkpoint(on_checkpoint, {**ck, "_status": "failed", "_reply": fail_step["content"], "_error": detail})
            yield {
                "event": "done",
                "data": {
                    "reply": fail_step["content"],
                    "steps": steps,
                    "budget": {"used": budget_used, "max": budget_max, "unit": "steps"},
                    "identity": identity,
                    "ok": False,
                },
            }
            return
        except Exception:
            raise

        if decision["type"] == "final":
            step = {
                "index": budget_used,
                "kind": "final",
                "content": decision["content"],
            }
            steps.append(step)
            yield {"event": "final", "data": step}
            ck = _checkpoint_payload(
                message=message,
                history=hist,
                tool_results=tool_results,
                steps=steps,
                budget_used=budget_used,
            )
            await _emit_checkpoint(
                on_checkpoint,
                {**ck, "_status": "completed", "_reply": decision["content"]},
            )
            payload = {
                "reply": decision["content"],
                "steps": steps,
                "budget": {"used": budget_used, "max": budget_max, "unit": "steps"},
                "identity": identity,
            }
            yield {"event": "done", "data": payload}
            return

        name = decision["name"]
        args = _inject_tenant_args(name, decision.get("arguments") or {}, identity)
        call_id = decision.get("call_id") or f"call_{uuid4().hex[:8]}"

        ok_tool, deny_reason = assert_tool_allowed(identity["role"], name)
        call_step = {
            "index": budget_used,
            "kind": "tool_call",
            "name": name,
            "arguments": args,
        }
        steps.append(call_step)
        yield {"event": "tool_call", "data": call_step}

        if not ok_tool:
            result = {"ok": False, "error": deny_reason, "denied": True}
        else:
            result = await run_tool_async(name, args)

        plant = identity.get("plant_filter")
        if (
            plant
            and result.get("ok")
            and isinstance(result.get("result"), dict)
            and "items" in result["result"]
            and name in {"list_open_hazards", "query_hazard_ledger"}
        ):
            items = [
                it
                for it in result["result"]["items"]
                if plant in str(it.get("plant") or "")
            ]
            result = {
                **result,
                "result": {
                    **result["result"],
                    "items": items,
                    "count": len(items),
                    "tenant_plant_filter": plant,
                },
            }

        result_step = {
            "index": budget_used,
            "kind": "tool_result",
            "name": name,
            "result": result,
        }
        if not result.get("ok", True) and result.get("timeout_s") is not None:
            result_step["note"] = "tool_timeout"
        steps.append(result_step)
        yield {"event": "tool_result", "data": result_step}

        tool_results.append(
            {"name": name, "arguments": args, "result": result, "call_id": call_id}
        )

        ck = _checkpoint_payload(
            message=message,
            history=hist,
            tool_results=tool_results,
            steps=steps,
            budget_used=budget_used,
        )
        await _emit_checkpoint(on_checkpoint, {**ck, "_status": "running"})

        # Teaching / crash drill: pause after N completed steps (post tool_result)
        if pause_after_steps is not None and budget_used >= pause_after_steps:
            detail = f"教学暂停：pause_after_steps={pause_after_steps}，可调用 resume 续跑"
            await _emit_checkpoint(
                on_checkpoint,
                {**ck, "_status": "paused", "_reply": detail},
            )
            yield {
                "event": "paused",
                "data": {
                    "detail": detail,
                    "steps": steps,
                    "budget": {"used": budget_used, "max": budget_max, "unit": "steps"},
                    "checkpoint": ck,
                },
            }
            return

    fallback = "已达到最大步数预算，请缩小问题或提高 MAX_AGENT_STEPS。"
    step = {"index": budget_used, "kind": "final", "content": fallback}
    steps.append(step)
    yield {"event": "final", "data": step}
    ck = _checkpoint_payload(
        message=message,
        history=hist,
        tool_results=tool_results,
        steps=steps,
        budget_used=budget_used,
    )
    await _emit_checkpoint(on_checkpoint, {**ck, "_status": "completed", "_reply": fallback})
    yield {
        "event": "done",
        "data": {
            "reply": fallback,
            "steps": steps,
            "budget": {"used": budget_used, "max": budget_max, "unit": "steps"},
            "identity": identity,
        },
    }
