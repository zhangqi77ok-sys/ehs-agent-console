"""Tool registry: schemas for the agent + dispatch into domain tools."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from app.config import settings
from app.tools.domain_tools import (
    ToolContext,
    advance_corrective_ticket,
    create_corrective_ticket,
    list_corrective_tickets,
    list_open_hazards,
    query_hazard_ledger,
    search_regulations,
)

ToolFn = Callable[..., dict]


TOOLS: dict[str, ToolFn] = {
    "search_regulations": search_regulations,
    "query_hazard_ledger": query_hazard_ledger,
    "list_open_hazards": list_open_hazards,
    "create_corrective_ticket": create_corrective_ticket,
    "list_corrective_tickets": list_corrective_tickets,
    "advance_corrective_ticket": advance_corrective_ticket,
}

WRITE_TOOLS = frozenset({"create_corrective_ticket", "advance_corrective_ticket"})

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_regulations",
        "description": "检索厂区 EHS 制度/法规条文（RAG），按 query 返回相关片段。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "query_hazard_ledger",
        "description": "查询隐患台账，可按 keyword/status/level/plant 过滤。",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "status": {"type": "string"},
                "level": {"type": "string"},
                "plant": {"type": "string"},
            },
        },
    },
    {
        "name": "list_open_hazards",
        "description": "列出未闭环隐患（待整改/整改中）。",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "create_corrective_ticket",
        "description": "对隐患开整改单（走领域 CAPA/审计）。",
        "parameters": {
            "type": "object",
            "properties": {
                "hazard_id": {"type": "string"},
                "measures": {"type": "string"},
                "action": {"type": "string"},
                "owner": {"type": "string"},
                "assignee": {"type": "string"},
                "due_days": {"type": "integer"},
            },
            "required": ["hazard_id"],
        },
    },
    {
        "name": "list_corrective_tickets",
        "description": "查询整改单列表。",
        "parameters": {
            "type": "object",
            "properties": {
                "hazard_id": {"type": "string"},
                "status": {"type": "string"},
            },
        },
    },
    {
        "name": "advance_corrective_ticket",
        "description": "推进整改单：start / submit_verify / close / reject。close 需 evidence_note。",
        "parameters": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "action": {"type": "string"},
                "evidence_note": {"type": "string"},
            },
            "required": ["ticket_id", "action"],
        },
    },
]


def schemas_for_tools(allowed: set[str] | None = None) -> list[dict[str, Any]]:
    if allowed is None:
        return list(TOOL_SCHEMAS)
    return [s for s in TOOL_SCHEMAS if s["name"] in allowed]


def run_tool(name: str, args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    fn = TOOLS.get(name)
    if not fn:
        return {"ok": False, "error": f"未知工具: {name}"}
    try:
        return fn(ctx, **(args or {}))
    except TypeError as exc:
        return {"ok": False, "error": f"工具参数错误: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


async def run_tool_async(name: str, args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(run_tool, name, args, ctx),
            timeout=settings.tool_timeout_s,
        )
    except asyncio.TimeoutError:
        return {"ok": False, "error": f"工具超时（>{settings.tool_timeout_s}s）", "timeout": True}
