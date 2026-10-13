"""Eng-03: request_id observability + JWT/API key auth."""

from __future__ import annotations

import pytest

from app.config import settings
from app.auth.jwt_tokens import issue_token, verify_token


def test_health_exposes_auth_and_obs(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("X-Request-Id")
    body = r.json()
    assert body.get("observability")
    assert body.get("auth_mode") in {"hybrid", "headers", "strict"}


def test_propagates_client_request_id(client):
    r = client.get("/health", headers={"X-Request-Id": "test-rid-123"})
    assert r.headers.get("X-Request-Id") == "test-rid-123"


def test_api_key_sets_tenant_plant_filter(client):
    r = client.get("/api/hazards", headers={"X-API-Key": "demo-plant-a"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items
    assert all("一号车间" in (h.get("plant") or "") for h in items)


def test_api_key_viewer_forbidden_write(client):
    r = client.post(
        "/api/tickets",
        headers={"X-API-Key": "demo-viewer"},
        json={"hazard_id": "HZ-2026-001", "measures": "不应成功"},
    )
    assert r.status_code == 403


def test_bad_api_key_401(client):
    r = client.get("/api/hazards", headers={"X-API-Key": "no-such-key"})
    assert r.status_code == 401


def test_jwt_roundtrip_and_me(client):
    tok = client.post("/api/auth/token", json={"api_key": "demo-plant-b"})
    assert tok.status_code == 200
    access = tok.json()["access_token"]
    claims = verify_token(access)
    assert claims["tenant_id"] == "plant_b"
    assert claims["role"] == "viewer"

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    ident = me.json()["identity"]
    assert ident["tenant_id"] == "plant_b"
    assert ident["auth_method"] == "jwt"


def test_jwt_wins_over_spoofed_headers(client):
    issued = issue_token(tenant_id="plant_a", role="ehs_engineer")
    r = client.get(
        "/api/domain/summary",
        headers={
            "Authorization": f"Bearer {issued['access_token']}",
            "X-Tenant-Id": "hq",
            "X-Role": "admin",
        },
    )
    assert r.status_code == 200
    ident = r.json()["identity"]
    assert ident["tenant_id"] == "plant_a"
    assert ident["role"] == "ehs_engineer"
    assert ident["auth_method"] == "jwt"


def test_strict_mode_rejects_headers_only(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "strict")
    r = client.get(
        "/api/hazards",
        headers={"X-Tenant-Id": "default", "X-Role": "admin"},
    )
    assert r.status_code == 401
    # reset not strictly needed — process ends; but keep hybrid for later fixtures
    monkeypatch.setattr(settings, "auth_mode", "hybrid")


def test_strict_mode_accepts_api_key(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "strict")
    r = client.get("/api/hazards", headers={"X-API-Key": "demo-engineer"})
    assert r.status_code == 200
    monkeypatch.setattr(settings, "auth_mode", "hybrid")


def test_demo_login_token(client):
    r = client.post(
        "/api/auth/token",
        json={
            "tenant_id": "hq",
            "role": "admin",
            "demo_secret": settings.demo_login_secret,
        },
    )
    assert r.status_code == 200
    assert r.json()["access_token"]
