"""JWKS / OIDC-lite JWT validation (Ch19).

When AUTH_JWKS_URL is set, RS256 (and other asymmetric) Bearer tokens are
verified against the remote JWKS. Local HS256 tokens from /auth/token still
use jwt_secret. This is NOT a full OIDC IdP (no authorize/token/userinfo).
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import jwt
from fastapi import HTTPException
from jwt import PyJWKClient

import app.config as config_mod

_jwk_client: PyJWKClient | None = None
_jwk_url: str = ""
_jwk_fetched_at: float = 0.0
_CACHE_TTL_S = 300.0


def _get_jwk_client(url: str) -> PyJWKClient:
    global _jwk_client, _jwk_url, _jwk_fetched_at
    now = time.time()
    if _jwk_client is None or _jwk_url != url or (now - _jwk_fetched_at) > _CACHE_TTL_S:
        _jwk_client = PyJWKClient(url, cache_keys=True, lifespan=_CACHE_TTL_S)
        _jwk_url = url
        _jwk_fetched_at = now
    return _jwk_client


def reset_jwks_cache() -> None:
    """Test helper."""
    global _jwk_client, _jwk_url, _jwk_fetched_at
    _jwk_client = None
    _jwk_url = ""
    _jwk_fetched_at = 0.0


def jwks_enabled() -> bool:
    return bool((config_mod.settings.auth_jwks_url or "").strip())


def decode_token_via_jwks(token: str, *, jwks_url: str | None = None) -> dict[str, Any]:
    url = (jwks_url if jwks_url is not None else config_mod.settings.auth_jwks_url or "").strip()
    if not url:
        raise HTTPException(status_code=401, detail="JWKS URL 未配置")
    try:
        client = _get_jwk_client(url)
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
            options={"require": ["exp"]},
        )
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="JWT 已过期") from exc
    except jwt.PyJWKClientError as exc:
        raise HTTPException(status_code=401, detail=f"JWKS 不可用: {exc}") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="JWT 无效（JWKS）") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=401, detail=f"JWKS 拉取失败: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 — surface as 401 for auth path
        raise HTTPException(status_code=401, detail=f"JWKS 校验失败: {exc}") from exc

    tenant_id = str(payload.get("tenant_id") or payload.get("tid") or "").strip()
    if not tenant_id:
        raise HTTPException(status_code=401, detail="JWT 缺少 tenant_id")
    role = str(payload.get("role") or "viewer").strip()
    from app.auth.jwt_tokens import ROLES

    if role not in ROLES:
        role = "viewer"
    actor = str(payload.get("actor") or payload.get("sub") or role).strip() or role
    return {"tenant_id": tenant_id, "role": role, "actor": actor, "auth": "jwks"}


def peek_alg(token: str) -> str | None:
    try:
        header = jwt.get_unverified_header(token)
        return str(header.get("alg") or "") or None
    except Exception:  # noqa: BLE001
        return None
