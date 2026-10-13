"""Aggregate run / HITL / deny metrics (Ch13)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select

from app.db.models import AgentApproval, AgentRun
from app.db import session as db_session
from app.runs.trace import classify_failure


def build_obs_summary(*, tenant_id: str | None = None) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        q = select(AgentRun)
        if tenant_id:
            q = q.where(AgentRun.tenant_id == tenant_id)
        runs = list(db.scalars(q).all())

        by_status: dict[str, int] = {}
        total_steps = 0
        failure_modes: dict[str, int] = {}
        deny_events = 0
        tool_result_events = 0

        for r in runs:
            by_status[r.status] = by_status.get(r.status, 0) + 1
            total_steps += int(r.budget_used or 0)
            try:
                steps = json.loads(r.steps_json or "[]")
            except json.JSONDecodeError:
                steps = []
            fm = classify_failure(steps, r.status, r.error or "")
            failure_modes[fm] = failure_modes.get(fm, 0) + 1
            for s in steps:
                if s.get("kind") != "tool_result":
                    continue
                tool_result_events += 1
                res = s.get("result") or {}
                if isinstance(res, dict) and res.get("denied"):
                    deny_events += 1

        run_ids = [r.run_id for r in runs]
        pending = 0
        if run_ids:
            aq = select(AgentApproval).where(
                AgentApproval.status == "pending",
                AgentApproval.run_id.in_(run_ids),
            )
            pending = len(list(db.scalars(aq).all()))

        avg_steps = round(total_steps / len(runs), 2) if runs else 0.0
        deny_rate = round(deny_events / tool_result_events, 4) if tool_result_events else 0.0

        return {
            "run_count": len(runs),
            "runs_by_status": by_status,
            "hitl_pending": pending,
            "tool_result_events": tool_result_events,
            "tool_deny_events": deny_events,
            "tool_deny_rate": deny_rate,
            "avg_steps": avg_steps,
            "failure_modes": failure_modes,
            "tenant_id": tenant_id,
        }
    finally:
        db.close()
