"""Multi-agent Supervisor: route to Investigator (read) or Clerk (write) (Ch11)."""

from __future__ import annotations

import re
from typing import Any, AsyncIterator

from sqlalchemy.orm import Session

from app.agent.loop import run_agent, stream_agent
from app.tools.registry import READ_TOOLS, WRITE_TOOLS

INVESTIGATOR_TOOLS = frozenset(READ_TOOLS)
CLERK_TOOLS = frozenset(READ_TOOLS | WRITE_TOOLS)


def route_intent(message: str) -> str:
    """Return 'clerk' for write intents, else 'investigator'."""
    text = message or ""
    write_kw = (
        "开整改单",
        "开单",
        "创建整改",
        "推进",
        "验收",
        "关闭",
        "驳回",
        "开始执行",
        "提交验收",
        "纠正",
    )
    if any(k in text for k in write_kw):
        return "clerk"
    if re.search(r"HZ-?\d{4}-?\d{3}", text, re.I) and any(
        k in text for k in ("开", "整改", "措施")
    ):
        return "clerk"
    if re.search(r"(TK|CA)-?\d+", text, re.I) and any(
        k in text for k in ("推进", "验收", "关闭", "驳回", "开始", "提交")
    ):
        return "clerk"
    return "investigator"


async def stream_supervised(
    message: str,
    session: Session,
    **kwargs: Any,
) -> AsyncIterator[dict[str, Any]]:
    role = route_intent(message)
    if role == "clerk":
        agent_label = "clerk"
        allowed = set(CLERK_TOOLS)
        detail = "Supervisor → Clerk（写工具可用，仍受 HITL/ACL）"
    else:
        agent_label = "investigator"
        allowed = set(INVESTIGATOR_TOOLS)
        detail = "Supervisor → Investigator（只读工具）"

    yield {
        "event": "supervisor",
        "data": {
            "route": agent_label,
            "detail": detail,
            "allowed_tools": sorted(allowed),
        },
    }
    note = {
        "index": 0,
        "kind": "note",
        "note": "supervisor_route",
        "detail": detail,
        "agent": "supervisor",
        "route": agent_label,
    }
    yield {"event": "note", "data": note}

    async for evt in stream_agent(
        message,
        session,
        allowed_tools=allowed,
        agent_label=agent_label,
        **kwargs,
    ):
        # prepend supervisor note into done.steps
        if evt["event"] == "done":
            data = dict(evt["data"])
            steps = list(data.get("steps") or [])
            if not any(s.get("note") == "supervisor_route" for s in steps):
                steps = [note] + steps
            data["steps"] = steps
            data["supervisor"] = {"route": agent_label, "detail": detail}
            yield {"event": "done", "data": data}
        else:
            yield evt


async def run_supervised(message: str, session: Session, **kwargs: Any) -> dict[str, Any]:
    reply = ""
    steps: list[dict] = []
    budget: dict[str, Any] = {}
    identity: dict[str, Any] = {}
    status = "completed"
    supervisor: dict[str, Any] = {}
    async for evt in stream_supervised(message, session, **kwargs):
        name = evt["event"]
        data = evt["data"]
        if name == "supervisor":
            supervisor = data
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
            supervisor = data.get("supervisor") or supervisor
            if data.get("ok") is False and status == "completed":
                status = "failed"
    return {
        "reply": reply,
        "steps": steps,
        "budget": budget,
        "identity": identity,
        "status": status,
        "supervisor": supervisor,
    }
