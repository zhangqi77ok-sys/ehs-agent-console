"""Ch19: JWKS / OIDC-lite JWT validation with static keyset fixture."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth.jwks import reset_jwks_cache


@pytest.fixture()
def rsa_jwks_server():
    """Spin a tiny JWKS HTTP server with one RSA key."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    # Build JWK via PyJWT
    from jwt.algorithms import RSAAlgorithm

    jwk = json.loads(RSAAlgorithm.to_jwk(public_key))
    jwk["kid"] = "test-key-1"
    jwk["alg"] = "RS256"
    jwk["use"] = "sig"
    jwks_doc = {"keys": [jwk]}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path.startswith("/.well-known/jwks.json"):
                body = json.dumps(jwks_doc).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):  # noqa: ARG002
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}/.well-known/jwks.json"
    yield {
        "url": url,
        "private_key": private_key,
        "public_pem": public_pem,
        "kid": "test-key-1",
    }
    server.shutdown()
    reset_jwks_cache()


def _mint_rs256(private_key, kid: str, **claims) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": claims.get("actor", "oidc-user"),
        "tenant_id": claims.get("tenant_id", "demo-plant"),
        "role": claims.get("role", "ehs_engineer"),
        "actor": claims.get("actor", "oidc-user"),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": kid})


def test_jwks_bearer_accepted(client, rsa_jwks_server, monkeypatch):
    from app.config import Settings
    import app.config as config_mod

    reset_jwks_cache()
    config_mod.settings = Settings(
        database_url=str(config_mod.settings.database_url),
        auth_jwks_url=rsa_jwks_server["url"],
        jwt_secret=config_mod.settings.jwt_secret,
    )
    token = _mint_rs256(
        rsa_jwks_server["private_key"],
        rsa_jwks_server["kid"],
        actor="jwks-eng",
    )
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    data = me.json()
    assert data["auth"] == "jwks"
    assert data["tenant_id"] == "demo-plant"
    assert data["role"] == "ehs_engineer"
    assert data["actor"] == "jwks-eng"

    hazards = client.get("/api/hazards", headers={"Authorization": f"Bearer {token}"})
    assert hazards.status_code == 200


def test_local_hs256_still_works_with_jwks_configured(client, rsa_jwks_server, monkeypatch):
    from app.config import Settings
    import app.config as config_mod

    reset_jwks_cache()
    config_mod.settings = Settings(
        database_url=str(config_mod.settings.database_url),
        auth_jwks_url=rsa_jwks_server["url"],
        jwt_secret=config_mod.settings.jwt_secret,
    )
    tok = client.post(
        "/auth/token",
        json={"tenant_id": "demo-plant", "role": "viewer", "actor": "local"},
    ).json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert me.status_code == 200
    assert me.json()["auth"] == "jwt"


def test_bad_rs256_rejected(client, rsa_jwks_server):
    from app.config import Settings
    import app.config as config_mod
    from cryptography.hazmat.primitives.asymmetric import rsa as rsa_mod

    reset_jwks_cache()
    config_mod.settings = Settings(
        database_url=str(config_mod.settings.database_url),
        auth_jwks_url=rsa_jwks_server["url"],
        jwt_secret=config_mod.settings.jwt_secret,
    )
    other = rsa_mod.generate_private_key(public_exponent=65537, key_size=2048)
    token = _mint_rs256(other, "test-key-1")
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
