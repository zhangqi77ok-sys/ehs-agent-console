"""Map MCP-like JSON schemas / calls onto the existing tool registry (Ch15).

Honest scope: this is a **compatible thin layer** (list tools + tools/call),
not a full MCP server with SSE transport / capability negotiation.
"""

from __future__ import annotations

from typing import Any

from app.tools.domain_tools import ToolContext
from app.tools.registry import TOOL_SCHEMAS, TOOLS, run_tool


def list_mcp_tools() -> list[dict[str, Any]]:
    """Expose tools in MCP tools/list-ish shape."""
    out = []
    for s in TOOL_SCHEMAS:
        out.append(
            {
                "name": s["name"],
                "description": s.get("description") or "",
                "inputSchema": s.get("parameters") or {"type": "object", "properties": {}},
            }
        )
    return out


def mcp_call_tool(
    name: str,
    arguments: dict[str, Any] | None,
    ctx: ToolContext,
    *,
    allowed: set[str] | None = None,
) -> dict[str, Any]:
    """Invoke via registry; preserve domain ACL / denied semantics."""
    if name not in TOOLS:
        return {
            "ok": False,
            "isError": True,
            "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
            "error": f"未知工具: {name}",
        }
    result = run_tool(name, arguments or {}, ctx, allowed=allowed)
    is_err = not result.get("ok", True)
    text = str(result.get("error") or result)
    return {
        "ok": result.get("ok", True),
        "isError": is_err,
        "denied": bool(result.get("denied")),
        "content": [{"type": "text", "text": text if is_err else _summarize(result)}],
        "structured": result,
        "name": name,
    }


def _summarize(result: dict[str, Any]) -> str:
    import json
    try:
        return json.dumps(result, ensure_ascii=False)[:2000]
    except TypeError:
        return str(result)[:2000]
