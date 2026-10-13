"""Request-scoped contextvars for structured logs."""

from __future__ import annotations

import contextvars

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
tenant_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("tenant_id", default="-")
role_var: contextvars.ContextVar[str] = contextvars.ContextVar("role", default="-")
