"""Ch8: JWT / API key / request_id observability."""

from __future__ import annotations


def test_issue_and_use_jwt(client, eng_headers):
    r = client.post(
        "/auth/token",
        json={"tenant_id": "demo-plant", "role": "ehs_engineer", "actor": "jwt-eng"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    token = body["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    data = me.json()
    assert data["tenant_id"] == "demo-plant"
    assert data["role"] == "ehs_engineer"
    assert data["actor"] == "jwt-eng"
    assert data["auth"] == "jwt"

    hazards = client.get("/api/hazards", headers={"Authorization": f"Bearer {token}"})
    assert hazards.status_code == 200
    assert isinstance(hazards.json(), list) and len(hazards.json()) >= 1


def test_api_key_auth(client):
    me = client.get("/auth/me", headers={"X-API-Key": "demo-key"})
    assert me.status_code == 200
    data = me.json()
    assert data["tenant_id"] == "demo-plant"
    assert data["role"] == "ehs_engineer"
    assert data["auth"] == "api_key"

    hazards = client.get("/api/hazards", headers={"X-API-Key": "demo-key"})
    assert hazards.status_code == 200


def test_invalid_api_key_401(client):
    r = client.get("/auth/me", headers={"X-API-Key": "nope"})
    assert r.status_code == 401


def test_invalid_jwt_401(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


def test_demo_headers_still_work(client, eng_headers):
    me = client.get("/auth/me", headers=eng_headers)
    assert me.status_code == 200
    assert me.json()["auth"] == "headers"


def test_request_id_echoed(client):
    r = client.get("/health", headers={"X-Request-Id": "req-test-001"})
    assert r.status_code == 200
    assert r.headers.get("X-Request-Id") == "req-test-001"


def test_request_id_generated_when_missing(client):
    r = client.get("/health")
    assert r.status_code == 200
    rid = r.headers.get("X-Request-Id")
    assert rid and len(rid) >= 8


def test_jwt_viewer_cannot_write(client):
    tok = client.post(
        "/auth/token",
        json={"tenant_id": "demo-plant", "role": "viewer", "actor": "v1"},
    ).json()["access_token"]
    r = client.post(
        "/api/tickets",
        headers={"Authorization": f"Bearer {tok}"},
        json={"hazard_id": "HZ-2026-001", "measures": "x", "owner": "a"},
    )
    assert r.status_code == 403


def test_refresh_and_logout_flow(client):
    from app.auth.refresh_store import reset_revocations

    reset_revocations()
    body = client.post(
        "/auth/token",
        json={"tenant_id": "demo-plant", "role": "admin", "actor": "admin-1"},
    ).json()
    refresh = body["refresh_token"]
    r = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    assert r.json()["access_token"]
    new_refresh = r.json()["refresh_token"]
    out = client.post("/auth/logout", json={"refresh_token": new_refresh})
    assert out.status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": new_refresh}).status_code == 401


def test_traceparent_echo(client):
    tp = "00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01"
    r = client.get("/health", headers={"traceparent": tp})
    assert r.headers.get("traceparent", "").startswith(
        "00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-"
    )
