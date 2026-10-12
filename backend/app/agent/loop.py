"""Handwritten Agent loop — observe → decide → act → observe …"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator
from uuid import uuid4

from ..config import settings
from ..tools.registry import TOOL_SCHEMAS, run_tool_async
from . import llm
from .llm import LLMCallError, LLMConfigError


async def run_agent(
    message: str,
    history: list[dict] | None = None,
    force_timeout: bool = False,
) -> dict[str, Any]:
    """Run to completion; returns final payload with steps for the UI."""
    steps: list[dict[str, Any]] = []
    reply = ""
    budget: dict[str, Any] = {"used": 0, "max": settings.max_agent_steps, "unit": "steps"}
    async for evt in stream_agent(message, history, force_timeout=force_timeout):
        name = evt["event"]
        data = evt["data"]
        if name in ("tool_call", "tool_result", "final", "note"):
            steps.append(data)
        if name == "final":
            reply = data.get("content") or ""
        if name == "budget":
            budget = data
        if name == "error":
            reply = data.get("detail") or reply
        if name == "done":
            reply = data.get("reply") or reply
            budget = data.get("budget") or budget
            steps = data.get("steps") or steps
    return {"reply": reply, "steps": steps, "budget": budget}


async def stream_agent(
    message: str,
    history: list[dict] | None = None,
    force_timeout: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    """Yield SSE events live as the agent runs (not after the full run).

    force_timeout: per-request teaching drill — tiny LLM HTTP timeout for this turn only.
    """
    steps: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    hist = list(history or [])
    budget_used = 0
    budget_max = settings.max_agent_steps

    yield {
        "event": "budget",
        "data": {"used": 0, "max": budget_max, "unit": "steps"},
    }

    if force_timeout:
        drill = {
            "index": 0,
            "kind": "note",
            "note": "force_timeout_drill",
            "detail": "本轮启用强制超时练习：LLM HTTP 超时约 0.05s，仍走真实网关路径。",
        }
        steps.append(drill)
        yield {"event": "note", "data": drill}

    for i in range(budget_max):
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
                TOOL_SCHEMAS,
                on_retry=on_retry,
                force_timeout=force_timeout,
            )
        )

        # Drain retry notes while the LLM call (and its backoff sleeps) is in flight.
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
            yield {
                "event": "done",
                "data": {
                    "reply": fail_step["content"],
                    "steps": steps,
                    "budget": {"used": budget_used, "max": budget_max, "unit": "steps"},
                    "ok": False,
                },
            }
            return
        except Exception:
            # Unexpected — re-raise so main.py can emit a generic error event.
            raise

        if decision["type"] == "final":
            step = {
                "index": budget_used,
                "kind": "final",
                "content": decision["content"],
            }
            steps.append(step)
            yield {"event": "final", "data": step}
            payload = {
                "reply": decision["content"],
                "steps": steps,
                "budget": {"used": budget_used, "max": budget_max, "unit": "steps"},
            }
            yield {"event": "done", "data": payload}
            return

        name = decision["name"]
        args = decision.get("arguments") or {}
        call_id = decision.get("call_id") or f"call_{uuid4().hex[:8]}"

        call_step = {
            "index": budget_used,
            "kind": "tool_call",
            "name": name,
            "arguments": args,
        }
        steps.append(call_step)
        yield {"event": "tool_call", "data": call_step}

        result = await run_tool_async(name, args)
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

    fallback = "已达到最大步数预算，请缩小问题或提高 MAX_AGENT_STEPS。"
    step = {"index": budget_used, "kind": "final", "content": fallback}
    steps.append(step)
    yield {"event": "final", "data": step}
    yield {
        "event": "done",
        "data": {
            "reply": fallback,
            "steps": steps,
            "budget": {"used": budget_used, "max": budget_max, "unit": "steps"},
        },
    }
