"""API key lookup (Ch8)."""

from __future__ import annotations

from fastapi import HTTPException

from app.auth.tenant import ROLES
from app.config import settings


def resolve_api_key(raw_key: str) -> dict:
    key = (raw_key or "").strip()
    if not key:
        raise HTTPException(status_code=401, detail="缺少 API Key")
    entry = settings.api_key_map.get(key)
    if not entry or not isinstance(entry, dict):
        raise HTTPException(status_code=401, detail="API Key 无效")
    tenant_id = str(entry.get("tenant_id") or "").strip()
    if not tenant_id:
        raise HTTPException(status_code=401, detail="API Key 未绑定租户")
    role = str(entry.get("role") or "viewer").strip()
    if role not in ROLES:
        role = "viewer"
    actor = str(entry.get("actor") or f"api-key:{key[:6]}").strip()
    return {"tenant_id": tenant_id, "role": role, "actor": actor, "auth": "api_key"}
