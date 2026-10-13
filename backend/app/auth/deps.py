from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.auth.tenant import domain_can_write, resolve_identity
from app.db import repo
from app.db.session import get_db


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


def deny_if_readonly(
    db: Session,
    identity: dict,
    *,
    action: str,
    target_type: str = "ticket",
    target_id: str = "",
) -> None:
    """Audit + 403 when role cannot write."""
    if domain_can_write(identity["role"]):
        return
    repo.append_audit(
        db,
        tenant_id=identity["tenant_id"],
        role=identity["role"],
        actor=identity["actor"],
        action="ticket.denied",
        target_type=target_type,
        target_id=target_id,
        payload={"attempted_action": action},
        ok=False,
        error="当前角色只读，禁止写操作",
    )
    db.commit()
    raise HTTPException(status_code=403, detail="当前角色只读，禁止写操作")


Identity = Annotated[dict, Depends(get_identity)]
WriteIdentity = Annotated[dict, Depends(require_write)]
