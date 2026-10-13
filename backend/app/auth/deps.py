"""Resolve caller identity: JWT / API key / (optional) demo headers."""

from __future__ import annotations

from typing import Any

from fastapi import Header, HTTPException, Request

from ..config import settings
from ..obs.context import role_var, tenant_id_var
from .api_keys import resolve_api_key
from .jwt_tokens import JwtError, verify_token
from .tenant import resolve_identity


def _attach(request: Request, identity: dict[str, Any], auth_method: str) -> dict[str, Any]:
    identity = {**identity, "auth_method": auth_method}
    request.state.tenant_id = identity.get("tenant_id")
    request.state.role = identity.get("role")
    request.state.auth_method = auth_method
    tenant_id_var.set(str(identity.get("tenant_id") or "-"))
    role_var.set(str(identity.get("role") or "-"))
    return identity


def get_current_identity(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_role: str | None = Header(default=None, alias="X-Role"),
) -> dict[str, Any]:
    """
    auth_mode:
      - headers: Ch8 demo headers only
      - hybrid (default): JWT or API key preferred; else headers (UI keeps working)
      - strict: JWT or API key required (headers alone → 401)
    """
    mode = (settings.auth_mode or "hybrid").strip().lower()

    bearer = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization[7:].strip()

    if bearer:
        try:
            claims = verify_token(bearer)
        except JwtError as exc:
            raise HTTPException(status_code=401, detail=f"无效 JWT：{exc}") from exc
        ident = resolve_identity(claims["tenant_id"], claims["role"])
        return _attach(request, ident, "jwt")

    if x_api_key:
        mapped = resolve_api_key(x_api_key)
        if not mapped:
            raise HTTPException(status_code=401, detail="无效 API Key")
        ident = resolve_identity(mapped["tenant_id"], mapped["role"])
        return _attach(request, ident, "api_key")

    if mode == "strict":
        raise HTTPException(
            status_code=401,
            detail="AUTH_MODE=strict：请提供 Authorization: Bearer <jwt> 或 X-API-Key",
        )

    # headers / hybrid fallback
    ident = resolve_identity(x_tenant_id, x_role)
    return _attach(request, ident, "headers")
