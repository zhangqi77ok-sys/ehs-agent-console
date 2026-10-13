from typing import Annotated

from fastapi import Depends, Header, HTTPException

from app.auth.tenant import domain_can_write, resolve_identity


def get_identity(
    x_tenant_id: Annotated[str | None, Header()] = None,
    x_role: Annotated[str | None, Header()] = None,
    x_actor: Annotated[str | None, Header()] = None,
) -> dict:
    headers = {}
    if x_tenant_id is not None:
        headers["X-Tenant-Id"] = x_tenant_id
    if x_role is not None:
        headers["X-Role"] = x_role
    if x_actor is not None:
        headers["X-Actor"] = x_actor
    return resolve_identity(headers)


def require_write(identity: Annotated[dict, Depends(get_identity)]) -> dict:
    if not domain_can_write(identity["role"]):
        raise HTTPException(status_code=403, detail="当前角色只读，禁止写操作")
    return identity


Identity = Annotated[dict, Depends(get_identity)]
WriteIdentity = Annotated[dict, Depends(require_write)]
