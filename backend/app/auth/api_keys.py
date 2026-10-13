"""API key → tenant/role mapping (env-configured)."""

from __future__ import annotations

from typing import Any

from ..config import settings


def _parse_keys(raw: str) -> dict[str, dict[str, str]]:
    """Format: key:tenant:role,key2:tenant:role"""
    out: dict[str, dict[str, str]] = {}
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        bits = part.split(":")
        if len(bits) != 3:
            continue
        key, tenant, role = (b.strip() for b in bits)
        if key:
            out[key] = {"tenant_id": tenant or "default", "role": role or "viewer"}
    return out


def load_api_keys() -> dict[str, dict[str, str]]:
    return _parse_keys(settings.api_keys)


def resolve_api_key(api_key: str | None) -> dict[str, Any] | None:
    if not api_key:
        return None
    mapping = load_api_keys().get(api_key.strip())
    if not mapping:
        return None
    return {"tenant_id": mapping["tenant_id"], "role": mapping["role"], "auth": "api_key"}
