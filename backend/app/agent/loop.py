"""Handwritten Agent loop — observe → decide → act → observe …"""

from __future__ import annotations

from typing import Any, AsyncIterator
from uuid import uuid4

from ..config import settings
from ..tools.registry import TOOL_SCHEMAS, run_tool
from . import llm


async def run_agent(message: str, history: list[dict] | None = None) -> dict[str, Any]:
    """Run to completion; returns final payload with steps for the UI."""
    steps: list[dict[str, Any]] = []
    reply = ""
    budget: dict[str, Any] = {"used": 0, "max": settings.max_agent_steps, "unit": "steps"}
    async for evt in stream_agent(message, history):
        name = evt["event"]
        data = evt["data"]
        if name in ("tool_call", "tool_result", "final"):
            steps.append(data)
        if name == "final":
            reply = data.get("content") or ""
        if name == "budget":
            budget = data
        if name == "done":
            reply = data.get("reply") or reply
            budget = data.get("budget") or budget
            steps = data.get("steps") or steps
    return {"reply": reply, "steps": steps, "budget": budget}


async def stream_agent(
    message: str, history: list[dict] | None = None
) -> AsyncIterator[dict[str, Any]]:
    """Yield SSE events live as the agent runs (not after the full run)."""
    steps: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    hist = list(history or [])
    budget_used = 0
    budget_max = settings.max_agent_steps

    yield {
        "event": "budget",
        "data": {"used": 0, "max": budget_max, "unit": "steps"},
    }

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

        decision = await llm.complete(message, hist, tool_results, TOOL_SCHEMAS)

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

        result = run_tool(name, args)
        result_step = {
            "index": budget_used,
            "kind": "tool_result",
            "name": name,
            "result": result,
        }
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
