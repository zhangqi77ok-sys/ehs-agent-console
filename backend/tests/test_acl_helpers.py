import pytest
from fastapi import HTTPException

from app.auth.tenant import ROLES, domain_can_write, resolve_identity


def test_viewer_cannot_write():
    assert domain_can_write("viewer") is False


def test_engineer_and_admin_can_write():
    assert domain_can_write("ehs_engineer") is True
    assert domain_can_write("admin") is True


def test_unknown_role_falls_back_to_viewer_readonly():
    assert domain_can_write("unknown") is False
    ident = resolve_identity({"X-Tenant-Id": "t1", "X-Role": "hacker"})
    assert ident["role"] == "viewer"
    assert domain_can_write(ident["role"]) is False


def test_resolve_identity_requires_tenant():
    with pytest.raises(HTTPException) as exc:
        resolve_identity({"X-Role": "ehs_engineer"})
    assert exc.value.status_code == 400


def test_resolve_identity_defaults():
    ident = resolve_identity({"X-Tenant-Id": "demo-plant"})
    assert ident["tenant_id"] == "demo-plant"
    assert ident["role"] == "viewer"
    assert ident["actor"] == "viewer"


def test_roles_catalog():
    assert "viewer" in ROLES
    assert "ehs_engineer" in ROLES
    assert "admin" in ROLES
