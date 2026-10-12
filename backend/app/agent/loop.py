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
    tool_results: list[dict[str, Any]] = []
    hist = list(history or [])
    budget_used = 0
    budget_max = settings.max_agent_steps

    for i in range(budget_max):
        budget_used = i + 1
        decision = await llm.complete(message, hist, tool_results, TOOL_SCHEMAS)
        if decision["type"] == "final":
            steps.append(
                {
                    "index": i + 1,
                    "kind": "final",
                    "content": decision["content"],
                }
            )
            return {
                "reply": decision["content"],
                "steps": steps,
                "budget": {"used": budget_used, "max": budget_max, "unit": "steps"},
            }

        name = decision["name"]
        args = decision.get("arguments") or {}
        call_id = decision.get("call_id") or f"call_{uuid4().hex[:8]}"
        steps.append(
            {
                "index": i + 1,
                "kind": "tool_call",
                "name": name,
                "arguments": args,
            }
        )
        result = run_tool(name, args)
        steps.append(
            {
                "index": i + 1,
                "kind": "tool_result",
                "name": name,
                "result": result,
            }
        )
        tool_results.append(
            {"name": name, "arguments": args, "result": result, "call_id": call_id}
        )

    fallback = "已达到最大步数预算，请缩小问题或提高 MAX_AGENT_STEPS。"
    steps.append({"index": budget_used, "kind": "final", "content": fallback})
    return {
        "reply": fallback,
        "steps": steps,
        "budget": {"used": budget_used, "max": budget_max, "unit": "steps"},
    }


async def stream_agent(message: str, history: list[dict] | None = None) -> AsyncIterator[dict[str, Any]]:
    """Yield step events then a final event (for SSE)."""
    result = await run_agent(message, history)
    for step in result["steps"]:
        yield {"event": "step", "data": step}
    yield {
        "event": "done",
        "data": {
            "reply": result["reply"],
            "budget": result["budget"],
            "steps": result["steps"],
        },
    }
