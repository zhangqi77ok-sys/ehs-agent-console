"""request_id + W3C traceparent + JSON access log middleware (Ch8 / hire-gate)."""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

access_logger = logging.getLogger("ehs.access")
if not access_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    access_logger.addHandler(handler)
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False

_TRACEPARENT_RE = re.compile(
    r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$",
    re.IGNORECASE,
)


def parse_or_make_traceparent(header: str | None) -> tuple[str, str, str]:
    """Return (traceparent, trace_id, span_id). Accept inbound or generate."""
    raw = (header or "").strip()
    m = _TRACEPARENT_RE.match(raw) if raw else None
    if m:
        version, trace_id, parent_id, flags = m.groups()
        # Continue the trace: keep trace_id, mint a new span_id as this hop.
        span_id = uuid.uuid4().hex[:16]
        traceparent = f"{version.lower()}-{trace_id.lower()}-{span_id}-{flags.lower()}"
        return traceparent, trace_id.lower(), span_id
    trace_id = uuid.uuid4().hex  # 32 hex
    span_id = uuid.uuid4().hex[:16]
    traceparent = f"00-{trace_id}-{span_id}-01"
    return traceparent, trace_id, span_id


class RequestIdAccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = (
            request.headers.get("X-Request-Id")
            or request.headers.get("x-request-id")
            or uuid.uuid4().hex
        )
        inbound_tp = request.headers.get("traceparent") or request.headers.get("Traceparent")
        traceparent, trace_id, span_id = parse_or_make_traceparent(inbound_tp)
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        request.state.span_id = span_id
        request.state.traceparent = traceparent
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            if settings.access_log_json:
                access_logger.info(
                    json.dumps(
                        {
                            "request_id": request_id,
                            "trace_id": trace_id,
                            "method": request.method,
                            "path": request.url.path,
                            "status": 500,
                            "duration_ms": int((time.perf_counter() - started) * 1000),
                            "client": request.client.host if request.client else "",
                        },
                        ensure_ascii=False,
                    )
                )
            raise
        response.headers["X-Request-Id"] = request_id
        response.headers["traceparent"] = traceparent
        if settings.access_log_json:
            access_logger.info(
                json.dumps(
                    {
                        "request_id": request_id,
                        "trace_id": trace_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status": status_code,
                        "duration_ms": int((time.perf_counter() - started) * 1000),
                        "client": request.client.host if request.client else "",
                    },
                    ensure_ascii=False,
                )
            )
        return response
