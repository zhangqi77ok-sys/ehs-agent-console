"""X-Request-Id propagation + structured access log."""

from __future__ import annotations

import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .context import request_id_var, role_var, tenant_id_var
from .logging_setup import access_logger, configure_logging


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, log_level: str = "INFO"):  # noqa: ANN001
        super().__init__(app)
        configure_logging(log_level)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        rid = (request.headers.get("x-request-id") or "").strip() or str(uuid.uuid4())
        token_rid = request_id_var.set(rid)
        request.state.request_id = rid
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-Id"] = rid
            return response
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            tenant = getattr(request.state, "tenant_id", None) or request.headers.get("x-tenant-id") or "-"
            role = getattr(request.state, "role", None) or request.headers.get("x-role") or "-"
            auth = getattr(request.state, "auth_method", None) or "-"
            access_logger.info(
                "request",
                extra={
                    "request_id": rid,
                    "method": request.method,
                    "path": request.url.path,
                    "status": status,
                    "duration_ms": duration_ms,
                    "tenant_id": tenant,
                    "role": role,
                    "auth": auth,
                },
            )
            request_id_var.reset(token_rid)
            # tenant/role vars may be set in deps — reset if present
            try:
                tenant_id_var.set("-")
                role_var.set("-")
            except Exception:  # noqa: BLE001
                pass
