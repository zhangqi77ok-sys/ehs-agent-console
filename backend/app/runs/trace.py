"""Build and persist span traces from run steps (Ch5)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select

from app.db.models import AgentSpan
from app.db import session as db_session


def _j(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


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
    }


def classify_failure(steps: list[dict[str, Any]], status: str, error: str = "") -> str:
    if status == "completed":
        return "ok"
    if status == "paused":
        return "paused"
    if status == "awaiting_approval":
        return "awaiting_approval"
    blob = " ".join(json.dumps(s, ensure_ascii=False) for s in steps) + " " + (error or "")
    low = blob.lower()
    if "超时" in blob or "timeout" in low:
        return "timeout"
    if "denied" in low or "无权" in blob or "只读" in blob:
        return "tool_denied"
    if "最大步数" in blob:
        return "budget_exhausted"
    if "调用失败" in blob or status == "failed":
        return "llm_or_runtime_error"
    return "unknown"


def replace_spans_from_steps(run_id: str, steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    db = db_session.SessionLocal()
    try:
        db.execute(delete(AgentSpan).where(AgentSpan.run_id == run_id))
        out: list[dict[str, Any]] = []
        root = f"span_{uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)
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
            created_at=now,
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
            span_kind = "note"
            if kind == "tool_call":
                span_kind = "tool"
                name = str(s.get("name") or "tool")
                inp = {"arguments": s.get("arguments") or {}}
            elif kind == "tool_result":
                span_kind = "tool"
                name = str(s.get("name") or "tool")
                result = s.get("result") or {}
                outp = result if isinstance(result, dict) else {"result": result}
                if isinstance(result, dict):
                    if result.get("denied"):
                        status = "denied"
                    elif result.get("ok") is False:
                        status = "error"
                    if result.get("timeout"):
                        status = "timeout"
            elif kind == "final":
                span_kind = "llm"
                name = "final"
                outp = {"content": s.get("content")}
                if str(s.get("content") or "").startswith("调用失败"):
                    status = "error"
            elif kind == "note":
                span_kind = "note"
                name = str(s.get("note") or "note")
                attrs = {k: v for k, v in s.items() if k not in {"index", "kind"}}
            row = AgentSpan(
                span_id=sid,
                run_id=run_id,
                parent_span_id=root,
                kind=span_kind,
                name=name,
                status=status,
                step_index=int(s.get("index") or 0),
                duration_ms=0,
                attrs_json=_j(attrs),
                input_json=_j(inp),
                output_json=_j(outp),
                created_at=now,
            )
            db.add(row)
            out.append(_span_dict(row))
        db.commit()
        return out
    finally:
        db.close()


def list_spans(run_id: str) -> list[dict[str, Any]]:
    db = db_session.SessionLocal()
    try:
        q = select(AgentSpan).where(AgentSpan.run_id == run_id).order_by(AgentSpan.step_index, AgentSpan.span_id)
        return [_span_dict(r) for r in db.scalars(q).all()]
    finally:
        db.close()
