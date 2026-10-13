"""Tenant/role identity helpers — single place to interpret headers."""

from __future__ import annotations

from fastapi import HTTPException

ROLES = ("viewer", "ehs_engineer", "admin")
WRITE_ROLES = frozenset({"ehs_engineer", "admin"})


def domain_can_write(role: str) -> bool:
    return role in WRITE_ROLES


def resolve_identity(headers: dict) -> dict:
    """Parse X-Tenant-Id / X-Role from a header mapping (case-insensitive keys ok)."""
    lower = {str(k).lower(): str(v) for k, v in headers.items()}
    tenant_id = (lower.get("x-tenant-id") or "").strip()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="缺少身份头 X-Tenant-Id")
    raw_role = (lower.get("x-role") or "viewer").strip()
    role = raw_role if raw_role in ROLES else "viewer"
    actor = (lower.get("x-actor") or role).strip() or role
    return {"tenant_id": tenant_id, "role": role, "actor": actor}
