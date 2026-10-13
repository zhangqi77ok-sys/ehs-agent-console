"""Multi-agent Supervisor: route to Investigator (read) or Clerk (write) (Ch11).

Can hand off Investigator → Clerk in one supervised turn so UI shows two role timelines.
"""

from __future__ import annotations

import re
from typing import Any, AsyncIterator

from sqlalchemy.orm import Session

from app.agent.loop import stream_agent
from app.tools.registry import READ_TOOLS, WRITE_TOOLS

INVESTIGATOR_TOOLS = frozenset(READ_TOOLS)
CLERK_TOOLS = frozenset(READ_TOOLS | WRITE_TOOLS)

_WRITE_KW = (
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
_LOOKUP_KW = (
    "查",
    "有哪些",
    "列表",
    "未闭环",
    "待整改",
    "灭火器",
    "配电",
    "重大",
    "制度",
    "法规",
)


def route_intent(message: str) -> str:
    """Return 'clerk' for write intents, else 'investigator'."""
    text = message or ""
    if any(k in text for k in _WRITE_KW):
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


def needs_investigator_handoff(message: str) -> bool:
    """Clerk path that still benefits from a prior read (dual timeline demo)."""
    text = message or ""
    if route_intent(text) != "clerk":
        return False
    if re.search(r"HZ-?\d{4}-?\d{3}", text, re.I):
        # already has id — optional lookup if also asks 查/列表
        return any(k in text for k in ("查", "先查", "有哪些", "确认"))
    return any(k in text for k in _LOOKUP_KW)


def _tag_steps(steps: list[dict], agent: str) -> list[dict]:
    out = []
    for s in steps:
        d = dict(s)
        d.setdefault("agent", agent)
        out.append(d)
    return out


async def _collect_child(
    message: str,
    session: Session,
    *,
    agent_label: str,
    allowed: set[str],
    kwargs: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    """Run one child stream; return (emitted_events_as_pairs, done_data, steps)."""
    events: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    done: dict[str, Any] = {}
    async for evt in stream_agent(
        message,
        session,
        allowed_tools=allowed,
        agent_label=agent_label,
        **kwargs,
    ):
        events.append(evt)
        if evt["event"] in ("tool_call", "tool_result", "final", "note"):
            steps.append(evt["data"])
        if evt["event"] == "done":
            done = evt["data"]
            steps = _tag_steps(done.get("steps") or steps, agent_label)
    return events, done, steps


async def stream_supervised(
    message: str,
    session: Session,
    **kwargs: Any,
) -> AsyncIterator[dict[str, Any]]:
    primary = route_intent(message)
    handoff = needs_investigator_handoff(message)

    plan = {
        "route": primary,
        "handoff": handoff,
        "detail": (
            "Supervisor → Investigator → Clerk（先读后写）"
            if handoff
            else (
                "Supervisor → Clerk（写工具可用，仍受 HITL/ACL）"
                if primary == "clerk"
                else "Supervisor → Investigator（只读工具）"
            )
        ),
        "timeline": ["supervisor"]
        + (["investigator", "clerk"] if handoff else [primary]),
    }
    yield {"event": "supervisor", "data": plan}
    note = {
        "index": 0,
        "kind": "note",
        "note": "supervisor_route",
        "detail": plan["detail"],
        "agent": "supervisor",
        "route": primary,
        "handoff": handoff,
    }
    yield {"event": "note", "data": note}

    all_steps: list[dict[str, Any]] = [note]
    final_reply = ""
    identity: dict[str, Any] = {}
    budget: dict[str, Any] = {}
    status = "completed"
    child_kwargs = {k: v for k, v in kwargs.items()}

    if handoff:
        # Phase 1: investigator — force a read-oriented prompt if needed
        # Strip write cues so mock LLM routes to read tools under Investigator allowlist.
        inv_msg = message
        for w in _WRITE_KW:
            inv_msg = inv_msg.replace(w, "查询")
        inv_msg = re.sub(r"措施[：:].*", "", inv_msg)
        inv_msg = re.sub(r"给\s*HZ-\d{4}-\d{3}", "关于相关隐患", inv_msg, flags=re.I)
        if "查" not in inv_msg and "隐患" in inv_msg:
            inv_msg = "查询隐患台账：" + inv_msg
        if "灭火器" in message and "灭火器" not in inv_msg:
            inv_msg = "查一下灭火器相关隐患"
        inv_msg = inv_msg.strip() or "有哪些未闭环隐患？"
        events, done, steps = await _collect_child(
            inv_msg,
            session,
            agent_label="investigator",
            allowed=set(INVESTIGATOR_TOOLS),
            kwargs={**child_kwargs, "hitl_enabled": False},
        )
        for evt in events:
            if evt["event"] == "done":
                continue
            yield evt
        all_steps.extend(steps)
        identity = done.get("identity") or identity
        budget = done.get("budget") or budget
        handoff_note = {
            "index": len(all_steps),
            "kind": "note",
            "note": "handoff",
            "detail": "Investigator 完成只读排查，交接 Clerk 执行写操作",
            "agent": "supervisor",
        }
        all_steps.append(handoff_note)
        yield {"event": "note", "data": handoff_note}
        yield {
            "event": "supervisor",
            "data": {**plan, "phase": "clerk", "detail": "交接 Clerk"},
        }

        events, done, steps = await _collect_child(
            message,
            session,
            agent_label="clerk",
            allowed=set(CLERK_TOOLS),
            kwargs=child_kwargs,
        )
        for evt in events:
            if evt["event"] == "done":
                continue
            yield evt
        all_steps.extend(steps)
        final_reply = done.get("reply") or final_reply
        identity = done.get("identity") or identity
        budget = done.get("budget") or budget
        status = done.get("status") or status
    else:
        agent_label = "clerk" if primary == "clerk" else "investigator"
        allowed = set(CLERK_TOOLS) if primary == "clerk" else set(INVESTIGATOR_TOOLS)
        events, done, steps = await _collect_child(
            message,
            session,
            agent_label=agent_label,
            allowed=allowed,
            kwargs=child_kwargs,
        )
        for evt in events:
            if evt["event"] == "done":
                continue
            yield evt
        all_steps.extend(steps)
        final_reply = done.get("reply") or ""
        identity = done.get("identity") or {}
        budget = done.get("budget") or {}
        status = done.get("status") or "completed"

    yield {
        "event": "done",
        "data": {
            "reply": final_reply,
            "steps": all_steps,
            "budget": budget,
            "identity": identity,
            "ok": status in {"completed", "paused", "awaiting_approval"},
            "status": status,
            "supervisor": plan,
        },
    }


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
            reply = data.get("content") or reply
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
