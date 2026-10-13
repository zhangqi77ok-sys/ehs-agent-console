"""Handwritten Agent loop — observe → decide → act → observe …"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator
from uuid import uuid4

from ..auth.tenant import assert_tool_allowed, resolve_identity
from ..config import settings
from ..tools.registry import TOOL_SCHEMAS, schemas_for_tools, run_tool_async
from . import llm
from .llm import LLMCallError, LLMConfigError


def _filter_schemas(allowed: set[str] | list[str]) -> list[dict[str, Any]]:
    allow = set(allowed)
    return schemas_for_tools(allow)


def _inject_tenant_args(name: str, args: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    out = dict(args or {})
    plant = identity.get("plant_filter")
    if plant and name in {"query_hazard_ledger", "list_open_hazards"}:
        # Soft scope: force plant filter for ledger queries when tenant is plant-scoped.
        if name == "query_hazard_ledger" and not out.get("plant"):
            out["plant"] = plant
    return out


async def run_agent(
    message: str,
    history: list[dict] | None = None,
    force_timeout: bool = False,
    tenant_id: str = "default",
    role: str = "ehs_engineer",
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    reply = ""
    budget: dict[str, Any] = {"used": 0, "max": settings.max_agent_steps, "unit": "steps"}
    identity: dict[str, Any] = {}
    async for evt in stream_agent(
        message,
        history,
        force_timeout=force_timeout,
        tenant_id=tenant_id,
        role=role,
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
        if name == "done":
            reply = data.get("reply") or reply
            budget = data.get("budget") or budget
            steps = data.get("steps") or steps
            identity = data.get("identity") or identity
    return {"reply": reply, "steps": steps, "budget": budget, "identity": identity}


async def stream_agent(
    message: str,
    history: list[dict] | None = None,
    force_timeout: bool = False,
    tenant_id: str = "default",
    role: str = "ehs_engineer",
) -> AsyncIterator[dict[str, Any]]:
    """Yield SSE events live as the agent runs.

    force_timeout: teaching drill — tiny LLM HTTP timeout for this turn only.
    tenant_id / role: Chapter 8 identity for tool allowlist + plant scope.
    """
    identity = resolve_identity(tenant_id, role)
    allowed = set(identity["allowed_tools"])
    schemas = _filter_schemas(allowed)

    steps: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    hist = list(history or [])
    budget_used = 0
    budget_max = settings.max_agent_steps

    yield {"event": "identity", "data": identity}
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

        # Extra plant scope filter on list results for plant tenants
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
            "identity": identity,
        },
    }
