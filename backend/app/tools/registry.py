"""Tool registry: schemas for the agent + dispatch."""

from __future__ import annotations

from typing import Any, Callable

from .hazard_ledger import create_corrective_ticket, list_open_hazards, query_hazard_ledger
from .rag_stub import search_regulations

ToolFn = Callable[..., dict]


TOOLS: dict[str, ToolFn] = {
    "query_hazard_ledger": query_hazard_ledger,
    "list_open_hazards": list_open_hazards,
    "create_corrective_ticket": create_corrective_ticket,
    "search_regulations": search_regulations,
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "query_hazard_ledger",
        "description": "查询 EHS 隐患台账。可按关键词、状态（待整改/整改中/已闭环）、级别（一般/重大）过滤。",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "标题或地点关键词"},
                "status": {"type": "string", "description": "状态过滤"},
                "level": {"type": "string", "description": "级别过滤"},
            },
        },
    },
    {
        "name": "list_open_hazards",
        "description": "列出所有未闭环的隐患（状态为「待整改」或「整改中」）。无需参数，适合回答「有哪些待整改/未闭环的隐患」。",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "create_corrective_ticket",
        "description": "针对已有隐患开整改单（纠正措施）。",
        "parameters": {
            "type": "object",
            "properties": {
                "hazard_id": {"type": "string", "description": "隐患编号，如 HZ-2026-001"},
                "action": {"type": "string", "description": "整改措施描述"},
                "assignee": {"type": "string", "description": "责任人"},
                "due_days": {"type": "integer", "description": "整改期限（天）"},
            },
            "required": ["hazard_id", "action"],
        },
    },
    {
        "name": "search_regulations",
        "description": "在示例 EHS 法规摘要中检索相关条款（v0 关键词 stub）。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "法规相关问题或关键词"},
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
