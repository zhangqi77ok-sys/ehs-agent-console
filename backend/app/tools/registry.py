"""Tool registry: schemas for the agent + dispatch."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from ..config import settings
from .hazard_ledger import (
    advance_corrective_ticket,
    create_corrective_ticket,
    list_corrective_tickets,
    list_open_hazards,
    query_hazard_ledger,
)
from .rag_stub import search_regulations

ToolFn = Callable[..., dict]


TOOLS: dict[str, ToolFn] = {
    "query_hazard_ledger": query_hazard_ledger,
    "list_open_hazards": list_open_hazards,
    "create_corrective_ticket": create_corrective_ticket,
    "list_corrective_tickets": list_corrective_tickets,
    "advance_corrective_ticket": advance_corrective_ticket,
    "search_regulations": search_regulations,
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "query_hazard_ledger",
        "description": (
            "查询 EHS 隐患台账。可按关键词、状态（待整改/整改中/待验收/已闭环/逾期）、"
            "级别（一般/重大）、车间 plant、类别 category、overdue_only 过滤。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "标题/描述/地点/编号关键词"},
                "status": {"type": "string", "description": "状态过滤；查逾期可用 status=逾期 或 overdue_only=true"},
                "level": {"type": "string", "description": "级别：一般/重大"},
                "plant": {"type": "string", "description": "车间/厂区，如 一号车间"},
                "category": {"type": "string", "description": "类别：消防/电气/机械/危化/动火/有限空间/环保等"},
                "overdue_only": {"type": "boolean", "description": "仅返回已逾期未闭环隐患"},
            },
        },
    },
    {
        "name": "list_open_hazards",
        "description": "列出未闭环隐患（待整改/整改中/待验收及逾期），重大与逾期优先。适合「有哪些未闭环/待整改」。",
        "parameters": {
            "type": "object",
            "properties": {
                "include_pending_verify": {
                    "type": "boolean",
                    "description": "是否包含待验收，默认 true",
                },
            },
        },
    },
    {
        "name": "create_corrective_ticket",
        "description": "针对未闭环隐患开整改单。已闭环或已有未关闭整改单会失败。",
        "parameters": {
            "type": "object",
            "properties": {
                "hazard_id": {"type": "string", "description": "隐患编号，如 HZ-2026-001"},
                "action": {"type": "string", "description": "整改措施（与 measures 同义）"},
                "measures": {"type": "string", "description": "整改措施描述"},
                "assignee": {"type": "string", "description": "责任人"},
                "owner": {"type": "string", "description": "责任人（优先）"},
                "due_days": {"type": "integer", "description": "整改期限（天），默认 7"},
            },
            "required": ["hazard_id"],
        },
    },
    {
        "name": "list_corrective_tickets",
        "description": "查询整改单列表，可按 hazard_id / status（待执行/执行中/待验收/已关闭）过滤。",
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
        "description": (
            "推进整改单状态机：start（待执行→执行中）、submit_verify（执行中→待验收）、"
            "close（待验收→已关闭并隐患闭环）、reject（待验收→执行中）。close/reject 可附 evidence_note。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "如 CA-101"},
                "action": {
                    "type": "string",
                    "description": "start | submit_verify | close | reject",
                },
                "evidence_note": {"type": "string", "description": "验收/驳回说明或证据摘要"},
            },
            "required": ["ticket_id", "action"],
        },
    },
    {
        "name": "search_regulations",
        "description": (
            "在 EHS 法规/制度摘要中做向量检索（切块 + 嵌入 + FAISS），"
            "返回带 score/heading/chunk_id 的条款；法规/闭环/双重预防/作业票类问题必用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "法规相关问题"},
                "top_k": {"type": "integer", "description": "返回条数，默认 3"},
            },
            "required": ["query"],
        },
    },
]


def run_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    if name not in TOOLS:
        return {"ok": False, "error": f"未知工具: {name}"}
    args = arguments or {}
    try:
        return {"ok": True, "result": TOOLS[name](**args)}
    except TypeError as e:
        return {"ok": False, "error": f"参数错误: {e}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


async def run_tool_async(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run a sync tool in a worker thread, bounded by TOOL_TIMEOUT_S."""
    timeout = float(settings.tool_timeout_s)
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(run_tool, name, arguments),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        return {
            "ok": False,
            "error": f"工具执行超时（>{timeout:g}s）: {name}",
            "timeout_s": timeout,
        }
