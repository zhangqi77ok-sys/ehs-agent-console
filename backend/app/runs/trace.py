"""Build and persist span traces from run steps (Ind-02)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select

from ..db.models import AgentSpan
from ..db.session import SessionLocal


def _j(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def classify_failure(steps: list[dict[str, Any]], status: str, error: str = "") -> str:
    if status == "completed":
        return "ok"
    if status == "paused":
        return "paused"
    blob = " ".join(json.dumps(s, ensure_ascii=False) for s in steps) + " " + (error or "")
    if "超时" in blob or "timeout" in blob.lower():
        return "timeout"
    if "denied" in blob or "无权" in blob:
        return "tool_denied"
    if "最大步数" in blob:
        return "budget_exhausted"
    if "调用失败" in blob or status == "failed":
        return "llm_or_runtime_error"
    return "unknown"


def replace_spans_from_steps(run_id: str, steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Derive spans from recorded steps (deterministic, no wall-clock needed)."""
    db = SessionLocal()
    try:
        db.execute(delete(AgentSpan).where(AgentSpan.run_id == run_id))
        out: list[dict[str, Any]] = []
        root = f"span_{uuid4().hex[:10]}"
        root_row = AgentSpan(
            span_id=root,
            run_id=run_id,
            parent_span_id=None,
            kind="run",
            name="agent_loop",
            status="ok",
            step_index=0,
            duration_ms=0,
            attrs_json="{}",
            input_json="{}",
            output_json="{}",
            created_at=datetime.utcnow(),
        )
        db.add(root_row)
        out.append(_span_dict(root_row))

        for s in steps:
            kind = s.get("kind") or "note"
            sid = f"span_{uuid4().hex[:10]}"
            status = "ok"
            name = kind
            inp: dict[str, Any] = {}
            outp: dict[str, Any] = {}
            attrs: dict[str, Any] = {}
            if kind == "tool_call":
                name = str(s.get("name") or "tool")
                inp = {"arguments": s.get("arguments") or {}}
            elif kind == "tool_result":
                name = str(s.get("name") or "tool")
                result = s.get("result") or {}
                outp = result if isinstance(result, dict) else {"result": result}
                if result.get("denied"):
                    status = "denied"
                elif result.get("ok") is False:
                    status = "error"
                if s.get("note") == "tool_timeout":
                    status = "timeout"
            elif kind == "final":
                name = "final"
                outp = {"content": s.get("content")}
                if str(s.get("content") or "").startswith("调用失败"):
                    status = "error"
            elif kind == "note":
                name = str(s.get("note") or "note")
                attrs = {k: v for k, v in s.items() if k not in {"index", "kind"}}
            row = AgentSpan(
                span_id=sid,
                run_id=run_id,
                parent_span_id=root,
                kind="llm" if kind == "final" and False else ("tool" if kind in {"tool_call", "tool_result"} else kind),
                name=name,
                status=status,
                step_index=int(s.get("index") or 0),
                duration_ms=0,
                attrs_json=_j(attrs),
                input_json=_j(inp),
                output_json=_j(outp),
                created_at=datetime.utcnow(),
            )
            # map kind more cleanly
            if kind == "tool_call":
                row.kind = "tool"
            elif kind == "tool_result":
                row.kind = "tool"
            elif kind == "final":
                row.kind = "llm"
            elif kind == "note":
                row.kind = "note"
            else:
                row.kind = str(kind)
            db.add(row)
            out.append(_span_dict(row))
        db.commit()
        return out
    finally:
        db.close()


def _span_dict(row: AgentSpan) -> dict[str, Any]:
    return {
        "span_id": row.span_id,
        "run_id": row.run_id,
        "parent_span_id": row.parent_span_id,
        "kind": row.kind,
        "name": row.name,
        "status": row.status,
        "step_index": row.step_index,
        "duration_ms": row.duration_ms,
        "attrs": json.loads(row.attrs_json or "{}"),
        "input": json.loads(row.input_json or "{}"),
        "output": json.loads(row.output_json or "{}"),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_spans(run_id: str) -> list[dict[str, Any]]:
    db = SessionLocal()
    try:
        rows = list(db.scalars(select(AgentSpan).where(AgentSpan.run_id == run_id).order_by(AgentSpan.created_at)).all())
        return [_span_dict(r) for r in rows]
    finally:
        db.close()
