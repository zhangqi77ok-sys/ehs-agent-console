"""Auth endpoints: issue JWT for demos / integrations (Ch8)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi import APIRouter, Header, HTTPException
from typing import Annotated

from app.auth.jwt_tokens import decode_token, issue_token
from app.auth.tenant import ROLES

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    role: str = "ehs_engineer"
    actor: str = ""
    expires_minutes: int | None = None


@router.post("/token")
def create_token(body: TokenRequest) -> dict:
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"role 必须是 {ROLES}")
    return issue_token(
        tenant_id=body.tenant_id,
        role=body.role,
        actor=body.actor,
        expires_minutes=body.expires_minutes,
    )


@router.get("/me")
def auth_me(
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    x_tenant_id: Annotated[str | None, Header()] = None,
    x_role: Annotated[str | None, Header()] = None,
    x_actor: Annotated[str | None, Header()] = None,
) -> dict:
    """Resolve current identity via JWT / API key / demo headers."""
    from app.auth.deps import resolve_request_identity

    return resolve_request_identity(
        authorization=authorization,
        x_api_key=x_api_key,
        x_tenant_id=x_tenant_id,
        x_role=x_role,
        x_actor=x_actor,
    )
