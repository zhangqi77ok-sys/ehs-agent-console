"""JWT issue/verify for multi-tenant identity (Ch8)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException

from app.config import settings

ROLES = ("viewer", "ehs_engineer", "admin")


def issue_token(
    *,
    tenant_id: str,
    role: str,
    actor: str = "",
    expires_minutes: int | None = None,
) -> dict[str, Any]:
    if not tenant_id.strip():
        raise HTTPException(status_code=400, detail="tenant_id 不能为空")
    role = role if role in ROLES else "viewer"
    actor = (actor or role).strip() or role
    minutes = expires_minutes if expires_minutes is not None else settings.jwt_expire_minutes
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=max(1, minutes))
    payload = {
        "sub": actor,
        "tenant_id": tenant_id.strip(),
        "role": role,
        "actor": actor,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": int((exp - now).total_seconds()),
        "tenant_id": payload["tenant_id"],
        "role": role,
        "actor": actor,
    }


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="JWT 已过期") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="JWT 无效") from exc
    tenant_id = str(payload.get("tenant_id") or "").strip()
    if not tenant_id:
        raise HTTPException(status_code=401, detail="JWT 缺少 tenant_id")
    role = str(payload.get("role") or "viewer").strip()
    if role not in ROLES:
        role = "viewer"
    actor = str(payload.get("actor") or payload.get("sub") or role).strip() or role
    return {"tenant_id": tenant_id, "role": role, "actor": actor, "auth": "jwt"}
