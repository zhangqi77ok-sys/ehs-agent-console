"""Auth token exchange + whoami."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..config import settings
from .api_keys import resolve_api_key
from .deps import get_current_identity
from .jwt_tokens import issue_token
from .tenant import ROLES, TENANTS, resolve_identity

router = APIRouter(prefix="/api/auth", tags=["auth"])


class TokenRequest(BaseModel):
    api_key: str | None = None
    tenant_id: str | None = None
    role: str | None = None
    demo_secret: str | None = Field(
        default=None,
        description="Only when AUTH_ALLOW_DEMO_LOGIN=true; must match DEMO_LOGIN_SECRET",
    )


@router.post("/token")
def create_token(body: TokenRequest) -> dict[str, Any]:
    """Exchange API key (or demo secret+tenant/role) for a JWT."""
    if body.api_key:
        mapped = resolve_api_key(body.api_key)
        if not mapped:
            raise HTTPException(status_code=401, detail="无效 API Key")
        return issue_token(tenant_id=mapped["tenant_id"], role=mapped["role"], sub="api_key")

    if settings.auth_allow_demo_login:
        secret = (body.demo_secret or "").strip()
        if not secret or secret != settings.demo_login_secret:
            raise HTTPException(status_code=401, detail="demo_secret 不正确")
        ident = resolve_identity(body.tenant_id, body.role)
        return issue_token(
            tenant_id=ident["tenant_id"], role=ident["role"], sub="demo_login"
        )

    raise HTTPException(
        status_code=400,
        detail="请提供 api_key；或开启 AUTH_ALLOW_DEMO_LOGIN 后用 demo_secret+tenant/role",
    )


@router.get("/me")
def auth_me(identity: dict[str, Any] = Depends(get_current_identity)) -> dict[str, Any]:
    return {"identity": identity, "auth_mode": settings.auth_mode}


@router.get("/meta")
def auth_meta() -> dict[str, Any]:
    return {
        "tenants": TENANTS,
        "roles": {
            k: {"label": v["label"], "tools": sorted(v["tools"]), "domain_write": v["domain_write"]}
            for k, v in ROLES.items()
        },
        "auth_mode": settings.auth_mode,
        "auth_methods": ["jwt", "api_key", "headers (hybrid/headers only)"],
    }
