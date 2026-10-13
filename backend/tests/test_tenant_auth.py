"""Pure unit tests for tenant/role resolution (Ch8 demo ACL)."""

from __future__ import annotations

from app.auth.tenant import assert_tool_allowed, domain_can_write, resolve_identity


def test_default_identity():
    ident = resolve_identity(None, None)
    assert ident["tenant_id"] == "default"
    assert ident["role"] == "ehs_engineer"
    assert ident["domain_write"] is True


def test_viewer_readonly_tools():
    ident = resolve_identity("plant_b", "viewer")
    assert ident["plant_filter"] == "三号车间"
    assert ident["domain_write"] is False
    ok, _ = assert_tool_allowed("viewer", "query_hazard_ledger")
    assert ok is True
    ok, msg = assert_tool_allowed("viewer", "create_corrective_ticket")
    assert ok is False
    assert "无权" in msg


def test_unknown_falls_back():
    ident = resolve_identity("no_such_tenant", "no_such_role")
    assert ident["tenant_id"] == "default"
    assert ident["role"] == "ehs_engineer"


def test_domain_can_write_helpers():
    assert domain_can_write("admin") is True
    assert domain_can_write("viewer") is False
