"""Chapter 8: multi-tenant + role allowlist (demo-grade, header-based)."""

from __future__ import annotations

from typing import Any

TENANTS: dict[str, dict[str, Any]] = {
    "default": {"name": "演示租户（全厂）", "plant_filter": None},
    "plant_a": {"name": "一号车间租户", "plant_filter": "一号车间"},
    "plant_b": {"name": "三号车间租户", "plant_filter": "三号车间"},
    "hq": {"name": "总部 EHS", "plant_filter": None},
}

# tool allowlists by role
ROLES: dict[str, dict[str, Any]] = {
    "viewer": {
        "label": "只读巡检",
        "tools": {
            "query_hazard_ledger",
            "list_open_hazards",
            "list_corrective_tickets",
            "search_regulations",
        },
        "domain_write": False,
    },
    "ehs_engineer": {
        "label": "EHS 工程师",
        "tools": {
            "query_hazard_ledger",
            "list_open_hazards",
            "list_corrective_tickets",
            "create_corrective_ticket",
            "advance_corrective_ticket",
            "search_regulations",
        },
        "domain_write": True,
    },
    "admin": {
        "label": "管理员",
        "tools": {
            "query_hazard_ledger",
            "list_open_hazards",
            "list_corrective_tickets",
            "create_corrective_ticket",
            "advance_corrective_ticket",
            "search_regulations",
        },
        "domain_write": True,
    },
}


def resolve_identity(
    tenant_id: str | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    tid = (tenant_id or "default").strip() or "default"
    rid = (role or "ehs_engineer").strip() or "ehs_engineer"
    if tid not in TENANTS:
        tid = "default"
    if rid not in ROLES:
        rid = "ehs_engineer"
    return {
        "tenant_id": tid,
        "tenant": TENANTS[tid],
        "role": rid,
        "role_meta": ROLES[rid],
        "plant_filter": TENANTS[tid].get("plant_filter"),
        "allowed_tools": sorted(ROLES[rid]["tools"]),
        "domain_write": bool(ROLES[rid]["domain_write"]),
    }


def assert_tool_allowed(role: str, tool_name: str) -> tuple[bool, str]:
    meta = ROLES.get(role) or ROLES["ehs_engineer"]
    if tool_name in meta["tools"]:
        return True, ""
    return False, f"角色「{role}」无权调用工具 {tool_name}"


def domain_can_write(role: str) -> bool:
    meta = ROLES.get(role) or ROLES["viewer"]
    return bool(meta.get("domain_write"))
