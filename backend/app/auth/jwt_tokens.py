"""JWT issue/verify for multi-tenant identity (Ch8 + Ch19 JWKS + refresh SSO-lite).

Access + refresh pair is 「企业登录前的自建 JWT 续期」— not Okta/OIDC.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException

from app.auth import refresh_store
from app.config import settings

ROLES = ("viewer", "ehs_engineer", "admin")


def _encode(payload: dict[str, Any]) -> str:
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def issue_token(
    *,
    tenant_id: str,
    role: str,
    actor: str = "",
    expires_minutes: int | None = None,
    include_refresh: bool = True,
) -> dict[str, Any]:
    if not tenant_id.strip():
        raise HTTPException(status_code=400, detail="tenant_id 不能为空")
    role = role if role in ROLES else "viewer"
    actor = (actor or role).strip() or role
    minutes = expires_minutes if expires_minutes is not None else settings.jwt_expire_minutes
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=max(1, minutes))
    access_jti = uuid.uuid4().hex
    access_payload = {
        "sub": actor,
        "tenant_id": tenant_id.strip(),
        "role": role,
        "actor": actor,
        "typ": "access",
        "jti": access_jti,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    access_token = _encode(access_payload)
    out: dict[str, Any] = {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": int((exp - now).total_seconds()),
        "tenant_id": access_payload["tenant_id"],
        "role": role,
        "actor": actor,
    }
    if include_refresh:
        refresh_days = max(1, int(settings.jwt_refresh_expire_days))
        refresh_exp = now + timedelta(days=refresh_days)
        refresh_jti = uuid.uuid4().hex
        refresh_payload = {
            "sub": actor,
            "tenant_id": access_payload["tenant_id"],
            "role": role,
            "actor": actor,
            "typ": "refresh",
            "jti": refresh_jti,
            "iat": int(now.timestamp()),
            "exp": int(refresh_exp.timestamp()),
        }
        out["refresh_token"] = _encode(refresh_payload)
        out["refresh_expires_in"] = int((refresh_exp - now).total_seconds())
    return out


def _raw_decode(token: str) -> dict[str, Any]:
    """Verify signature/exp; return raw claims. HS256 first, JWKS fallback for RS*."""
    from app.auth.jwks import decode_token_via_jwks, jwks_enabled, peek_alg

    alg = peek_alg(token)
    if alg and alg.startswith(("RS", "ES", "PS")) and jwks_enabled():
        # JWKS path returns identity-shaped dict already in some setups;
        # peal via raw jwt when possible — use jwks helper for verify only.
        return decode_token_via_jwks(token)

    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="JWT 已过期") from exc
    except jwt.InvalidTokenError as exc:
        if jwks_enabled():
            return decode_token_via_jwks(token)
        raise HTTPException(status_code=401, detail="JWT 无效") from exc


def _identity_from_claims(payload: dict[str, Any], *, expect_typ: str | None = "access") -> dict[str, Any]:
    typ = str(payload.get("typ") or "access").strip() or "access"
    if expect_typ and typ != expect_typ:
        raise HTTPException(status_code=401, detail=f"需要 {expect_typ} token，收到 typ={typ}")
    jti = str(payload.get("jti") or "").strip()
    if jti and refresh_store.is_revoked(jti):
        raise HTTPException(status_code=401, detail="token 已失效")
    tenant_id = str(payload.get("tenant_id") or "").strip()
    if not tenant_id:
        raise HTTPException(status_code=401, detail="JWT 缺少 tenant_id")
    role = str(payload.get("role") or "viewer").strip()
    if role not in ROLES:
        role = "viewer"
    actor = str(payload.get("actor") or payload.get("sub") or role).strip() or role
    return {
        "tenant_id": tenant_id,
        "role": role,
        "actor": actor,
        "auth": "jwt",
        "typ": typ,
        "jti": jti,
    }


def decode_token(token: str) -> dict[str, Any]:
    """Verify Bearer access JWT (typ=access or legacy without typ)."""
    payload = _raw_decode(token)
    # JWKS helper may already return identity dict without typ — treat as access.
    if "tenant_id" in payload and "role" in payload and "exp" not in payload and "typ" not in payload:
        return {
            "tenant_id": payload["tenant_id"],
            "role": payload.get("role") or "viewer",
            "actor": payload.get("actor") or payload.get("sub") or "viewer",
            "auth": payload.get("auth") or "jwt",
            "typ": "access",
            "jti": str(payload.get("jti") or ""),
        }
    typ = str(payload.get("typ") or "access").strip() or "access"
    if typ == "refresh":
        raise HTTPException(status_code=401, detail="refresh token 不能当 access 使用，请走 /auth/refresh")
    return _identity_from_claims(payload, expect_typ="access")


def decode_refresh_token(token: str) -> dict[str, Any]:
    payload = _raw_decode(token)
    return _identity_from_claims(payload, expect_typ="refresh")


def refresh_access_token(refresh_token: str, *, rotate_refresh: bool = True) -> dict[str, Any]:
    """Exchange refresh → new access (+ optional rotated refresh). Old refresh jti revoked on rotate."""
    ident = decode_refresh_token(refresh_token)
    if rotate_refresh and ident.get("jti"):
        refresh_store.revoke_jti(ident["jti"])
    return issue_token(
        tenant_id=ident["tenant_id"],
        role=ident["role"],
        actor=ident["actor"],
        include_refresh=rotate_refresh,
    )


def logout_refresh_token(refresh_token: str) -> dict[str, Any]:
    """Invalidate refresh jti so it cannot mint new access tokens."""
    try:
        ident = decode_refresh_token(refresh_token)
    except HTTPException as exc:
        # Already invalid / expired — treat logout as idempotent success for UX.
        if exc.status_code == 401:
            return {"ok": True, "revoked": False, "detail": str(exc.detail)}
        raise
    jti = ident.get("jti") or ""
    if jti:
        refresh_store.revoke_jti(jti)
    return {"ok": True, "revoked": bool(jti), "jti": jti}
