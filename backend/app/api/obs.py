"""Ch13: observability summary + span export."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.auth.deps import get_identity
from app.obs.summary import build_obs_summary
from app.runs.store import runs
from app.runs.trace import classify_failure, list_spans

router = APIRouter(tags=["observability"])


@router.get("/api/obs/summary")
def obs_summary(identity: dict[str, Any] = Depends(get_identity)) -> dict[str, Any]:
    tenant = None if identity.get("role") == "admin" else identity["tenant_id"]
    return build_obs_summary(tenant_id=tenant)


@router.get("/metrics")
def metrics_text(identity: dict[str, Any] = Depends(get_identity)) -> Response:
    """Prometheus-ish text exposition for interview talking points."""
    tenant = None if identity.get("role") == "admin" else identity["tenant_id"]
    s = build_obs_summary(tenant_id=tenant)
    lines = [
        "# HELP ehs_agent_runs_total Agent runs by status",
        "# TYPE ehs_agent_runs_total gauge",
    ]
    for st, n in (s.get("runs_by_status") or {}).items():
        lines.append(f'ehs_agent_runs_total{{status="{st}"}} {n}')
    lines.append("# HELP ehs_hitl_pending Pending HITL approvals")
    lines.append("# TYPE ehs_hitl_pending gauge")
    lines.append(f"ehs_hitl_pending {s['hitl_pending']}")
    lines.append("# HELP ehs_tool_deny_rate Fraction of tool_result denied")
    lines.append("# TYPE ehs_tool_deny_rate gauge")
    lines.append(f"ehs_tool_deny_rate {s['tool_deny_rate']}")
    lines.append("# HELP ehs_avg_steps Average budget_used per run")
    lines.append("# TYPE ehs_avg_steps gauge")
    lines.append(f"ehs_avg_steps {s['avg_steps']}")
    body = "\n".join(lines) + "\n"
    return Response(content=body, media_type="text/plain; version=0.0.4")


@router.get("/api/runs/{run_id}/spans/export")
def export_spans(run_id: str, identity: dict[str, Any] = Depends(get_identity)) -> Response:
    rec = runs.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="run not found")
    if rec["tenant_id"] != identity["tenant_id"] and identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="跨租户不可导出")
    spans = list_spans(run_id)
    payload = {
        "run_id": run_id,
        "status": rec["status"],
        "failure_mode": classify_failure(rec.get("steps") or [], rec["status"], rec.get("error") or ""),
        "span_count": len(spans),
        "spans": spans,
    }
    raw = json.dumps(payload, ensure_ascii=False, indent=2)
    return Response(
        content=raw,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="spans-{run_id}.json"'},
    )
