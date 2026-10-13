"""HS256 JWT issue/verify for demo multi-tenant auth."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from ..config import settings


class JwtError(Exception):
    pass


def issue_token(*, tenant_id: str, role: str, sub: str = "demo") -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    ttl = int(settings.jwt_ttl_s or 86400)
    payload = {
        "sub": sub,
        "tenant_id": tenant_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer", "expires_in": ttl, "claims": payload}


def verify_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "tenant_id", "role"]},
        )
    except jwt.PyJWTError as exc:
        raise JwtError(str(exc)) from exc
    return {
        "tenant_id": str(payload.get("tenant_id") or "default"),
        "role": str(payload.get("role") or "viewer"),
        "sub": str(payload.get("sub") or ""),
        "auth": "jwt",
    }
