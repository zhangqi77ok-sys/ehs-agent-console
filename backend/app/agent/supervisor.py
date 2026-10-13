"""Multi-agent Supervisor: Investigator / Clerk routing (Ch11) + parallel fan-out (Ch20).

Modes:
- single: Investigator or Clerk
- handoff: Investigator → Clerk (sequential, 先查再写)
- parallel: Investigator + Clerk fan-out with asyncio.gather, then join
"""

from __future__ import annotations

import asyncio
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
    "起草",
    "草案",
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
    "检索",
)
_PARALLEL_KW = ("同时", "并行", "一边", "同步", "一并", "一边查", "一边起草")


def route_intent(message: str) -> str:
    """Return 'clerk' for write intents, else 'investigator'."""
    text = message or ""
    if any(k in text for k in _WRITE_KW):
        return "clerk"
    if re.search(r"HZ-?\d{4}-?\d{3}", text, re.I) and any(
        k in text for k in ("开", "整改", "措施", "起草")
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
    if needs_parallel_fanout(text):
        return False
    if route_intent(text) != "clerk":
        return False
    if re.search(r"HZ-?\d{4}-?\d{3}", text, re.I):
        return any(k in text for k in ("查", "先查", "有哪些", "确认"))
    return any(k in text for k in _LOOKUP_KW)


def needs_parallel_fanout(message: str) -> bool:
    """Fan-out when user asks research + draft together (Ch20).

    Prefer explicit parallel cues (同时/并行/一边); also「查…并起草」without「先…再」.
    """
    text = message or ""
    research = (
        any(k in text for k in ("查", "检索", "制度", "法规", "有哪些", "列表", "未闭环"))
        or "隐患" in text
    )
    draft = any(k in text for k in ("起草", "草案", "开整改", "开单", "措施", "整改单"))
    if not (research and draft):
        return False
    # sequential handoff language wins
    if ("先" in text and "再" in text) or "先查" in text:
        return False
    if any(k in text for k in _PARALLEL_KW):
        return True
    if ("起草" in text or "草案" in text) and ("查" in text or "检索" in text or "制度" in text):
        return True
    return False


def _tag_steps(steps: list[dict], agent: str) -> list[dict]:
    out = []
    for s in steps:
        d = dict(s)
        d.setdefault("agent", agent)
        out.append(d)
    return out


def _investigator_prompt(message: str) -> str:
    inv_msg = message
    for w in _WRITE_KW:
        inv_msg = inv_msg.replace(w, "查询")
    inv_msg = re.sub(r"措施[：:].*", "", inv_msg)
    inv_msg = re.sub(r"给\s*HZ-\d{4}-\d{3}", "关于相关隐患", inv_msg, flags=re.I)
    if "查" not in inv_msg and "隐患" in inv_msg:
        inv_msg = "查询隐患台账：" + inv_msg
    if "灭火器" in message and "灭火器" not in inv_msg:
        inv_msg = "查一下灭火器相关隐患"
    if "制度" in message or "法规" in message:
        if "查制度" not in inv_msg and "检索" not in inv_msg:
            inv_msg = "查制度：" + (message if "灭火器" in message else inv_msg)
    return inv_msg.strip() or "有哪些未闭环隐患？"


def _clerk_prompt(message: str) -> str:
    """Keep write/draft cues for Clerk; strip research keywords so mock LLM routes to write tools."""
    text = message or ""
    for k in ("制度", "法规", "规定", "条例", "检索", "同时", "并行", "一边"):
        text = text.replace(k, "")
    text = text.strip(" ，,。；;、") or message
    return text.strip() or "请根据台账起草整改措施"


async def _collect_child(
    message: str,
    session: Session,
    *,
    agent_label: str,
    allowed: set[str],
    kwargs: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    """Run one child stream; return (events, done_data, steps)."""
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


def _fresh_session() -> Session:
    from app.db import session as db_session

    return db_session.SessionLocal()


async def stream_supervised(
    message: str,
    session: Session,
    **kwargs: Any,
) -> AsyncIterator[dict[str, Any]]:
    primary = route_intent(message)
    parallel = needs_parallel_fanout(message)
    handoff = False if parallel else needs_investigator_handoff(message)

    if parallel:
        timeline = ["supervisor", "investigator+clerk"]
        detail = "Supervisor → 并行 fan-out Investigator + Clerk，再合并结果"
        route_label = "parallel"
    elif handoff:
        timeline = ["supervisor", "investigator", "clerk"]
        detail = "Supervisor → Investigator → Clerk（先读后写）"
        route_label = primary
    elif primary == "clerk":
        timeline = ["supervisor", "clerk"]
        detail = "Supervisor → Clerk（写工具可用，仍受 HITL/ACL）"
        route_label = primary
    else:
        timeline = ["supervisor", "investigator"]
        detail = "Supervisor → Investigator（只读工具）"
        route_label = primary

    plan = {
        "route": route_label,
        "handoff": handoff,
        "parallel": parallel,
        "detail": detail,
        "timeline": timeline,
    }
    yield {"event": "supervisor", "data": plan}
    note = {
        "index": 0,
        "kind": "note",
        "note": "supervisor_route",
        "detail": plan["detail"],
        "agent": "supervisor",
        "route": route_label,
        "handoff": handoff,
        "parallel": parallel,
    }
    yield {"event": "note", "data": note}

    all_steps: list[dict[str, Any]] = [note]
    final_reply = ""
    identity: dict[str, Any] = {}
    budget: dict[str, Any] = {}
    status = "completed"
    child_kwargs = {k: v for k, v in kwargs.items()}

    if parallel:
        inv_msg = _investigator_prompt(message)
        clerk_msg = _clerk_prompt(message)
        # Separate DB sessions — SQLAlchemy Session is not concurrent-safe
        s_inv = _fresh_session()
        s_clerk = _fresh_session()
        try:
            (inv_events, inv_done, inv_steps), (clerk_events, clerk_done, clerk_steps) = (
                await asyncio.gather(
                    _collect_child(
                        inv_msg,
                        s_inv,
                        agent_label="investigator",
                        allowed=set(INVESTIGATOR_TOOLS),
                        kwargs={**child_kwargs, "hitl_enabled": False},
                    ),
                    _collect_child(
                        clerk_msg,
                        s_clerk,
                        agent_label="clerk",
                        allowed=set(CLERK_TOOLS),
                        kwargs=child_kwargs,
                    ),
                )
            )
        finally:
            s_inv.close()
            s_clerk.close()

        join_note = {
            "index": 1,
            "kind": "note",
            "note": "parallel_join",
            "detail": "并行分支已汇合：Investigator 调研 + Clerk 起草/开单",
            "agent": "supervisor",
            "parallel": True,
        }
        yield {"event": "note", "data": join_note}
        yield {
            "event": "supervisor",
            "data": {**plan, "phase": "join", "detail": "并行汇合"},
        }

        for evt in inv_events:
            if evt["event"] == "done":
                continue
            yield evt
        for evt in clerk_events:
            if evt["event"] == "done":
                continue
            yield evt

        all_steps.append(join_note)
        all_steps.extend(inv_steps)
        all_steps.extend(clerk_steps)

        inv_reply = (inv_done.get("reply") or "").strip()
        clerk_reply = (clerk_done.get("reply") or "").strip()
        parts = []
        if inv_reply:
            parts.append("【Investigator】\n" + inv_reply)
        if clerk_reply:
            parts.append("【Clerk】\n" + clerk_reply)
        final_reply = "\n\n".join(parts) or final_reply
        # prefer clerk identity/budget; merge used steps
        identity = clerk_done.get("identity") or inv_done.get("identity") or identity
        b_inv = inv_done.get("budget") or {}
        b_clerk = clerk_done.get("budget") or {}
        budget = {
            "used": int(b_inv.get("used") or 0) + int(b_clerk.get("used") or 0),
            "max": max(int(b_inv.get("max") or 0), int(b_clerk.get("max") or 0)),
        }
        st_inv = inv_done.get("status") or "completed"
        st_clerk = clerk_done.get("status") or "completed"
        if st_clerk in {"paused", "awaiting_approval", "failed"}:
            status = st_clerk
        elif st_inv == "failed":
            status = "failed"
        else:
            status = "completed"

        final_note = {
            "index": len(all_steps),
            "kind": "final",
            "content": final_reply,
            "agent": "supervisor",
        }
        all_steps.append(final_note)
        yield {"event": "final", "data": final_note}

    elif handoff:
        inv_msg = _investigator_prompt(message)
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
