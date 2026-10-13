"""Identity dependency — hybrid JWT / API key / demo headers (Ch8)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.auth.api_keys import resolve_api_key
from app.auth.jwt_tokens import decode_token
from app.auth.tenant import domain_can_write, resolve_identity
from app.config import settings
from app.db import repo
from app.db.session import get_db


def resolve_request_identity(
    *,
    authorization: str | None = None,
    x_api_key: str | None = None,
    x_tenant_id: str | None = None,
    x_role: str | None = None,
    x_actor: str | None = None,
) -> dict:
    """Priority: Bearer JWT → X-API-Key → demo X-Tenant-Id/X-Role headers."""
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token.strip():
            return decode_token(token.strip())
        if scheme.lower() == "bearer":
            raise HTTPException(status_code=401, detail="Bearer token 为空")

    if x_api_key:
        return resolve_api_key(x_api_key)

    if x_tenant_id or not settings.auth_require_credential:
        headers = {}
        if x_tenant_id is not None:
            headers["X-Tenant-Id"] = x_tenant_id
        if x_role is not None:
            headers["X-Role"] = x_role
        if x_actor is not None:
            headers["X-Actor"] = x_actor
        try:
            ident = resolve_identity(headers)
        except HTTPException:
            if settings.auth_require_credential:
                raise HTTPException(status_code=401, detail="需要 JWT、API Key 或 X-Tenant-Id") from None
            raise
        ident = {**ident, "auth": "headers"}
        return ident

    raise HTTPException(status_code=401, detail="需要 JWT、API Key 或 X-Tenant-Id")


def get_identity(
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    x_tenant_id: Annotated[str | None, Header()] = None,
    x_role: Annotated[str | None, Header()] = None,
    x_actor: Annotated[str | None, Header()] = None,
) -> dict:
    return resolve_request_identity(
        authorization=authorization,
        x_api_key=x_api_key,
        x_tenant_id=x_tenant_id,
        x_role=x_role,
        x_actor=x_actor,
    )


def require_write(identity: Annotated[dict, Depends(get_identity)]) -> dict:
    if not domain_can_write(identity["role"]):
        raise HTTPException(status_code=403, detail="当前角色只读，禁止写操作")
    return identity


def deny_if_readonly(
    db: Session,
    identity: dict,
    *,
    action: str,
    target_type: str = "ticket",
    target_id: str = "",
) -> None:
    """Audit + 403 when role cannot write."""
    if domain_can_write(identity["role"]):
        return
    repo.append_audit(
        db,
        tenant_id=identity["tenant_id"],
        role=identity["role"],
        actor=identity["actor"],
        action="ticket.denied",
        target_type=target_type,
        target_id=target_id,
        payload={"attempted_action": action},
        ok=False,
        error="当前角色只读，禁止写操作",
    )
    db.commit()
    raise HTTPException(status_code=403, detail="当前角色只读，禁止写操作")


Identity = Annotated[dict, Depends(get_identity)]
WriteIdentity = Annotated[dict, Depends(require_write)]
