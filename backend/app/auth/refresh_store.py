"""In-memory refresh-token revocation (portfolio SSO-lite).

Not a full IdP session store — just enough to invalidate refresh JTIs
after logout / rotation. Process restart clears the set (acceptable for demos).
"""

from __future__ import annotations

_revoked_jtis: set[str] = set()


def revoke_jti(jti: str) -> None:
    jti = (jti or "").strip()
    if jti:
        _revoked_jtis.add(jti)


def is_revoked(jti: str) -> bool:
    return (jti or "").strip() in _revoked_jtis


def reset_revocations() -> None:
    """Test helper."""
    _revoked_jtis.clear()
