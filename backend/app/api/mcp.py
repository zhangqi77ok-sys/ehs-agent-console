"""Ch15: MCP-style tools list + invoke endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import get_identity
from app.db.session import get_db
from app.mcp.adapter import list_mcp_tools, mcp_call_tool
from app.tools.domain_tools import ToolContext

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


class McpCallBody(BaseModel):
    name: str = Field(..., min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


@router.get("/tools")
def get_tools(identity: dict[str, Any] = Depends(get_identity)) -> dict[str, Any]:
    tools = list_mcp_tools()
    return {
        "protocol": "mcp-compatible-thin",
        "note": "JSON schema list + invoke only; not full MCP SSE transport",
        "tools": tools,
        "count": len(tools),
        "tenant_id": identity["tenant_id"],
    }


@router.post("/call")
def call_tool(
    body: McpCallBody,
    identity: dict[str, Any] = Depends(get_identity),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ctx = ToolContext(
        session=db,
        tenant_id=identity["tenant_id"],
        role=identity["role"],
        actor=identity.get("actor") or identity["role"],
    )
    return mcp_call_tool(body.name, body.arguments, ctx)
