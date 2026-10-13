"""request_id + JSON access log middleware (Ch8)."""

from __future__ import annotations

import json
import logging
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


class RequestIdAccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = (
            request.headers.get("X-Request-Id")
            or request.headers.get("x-request-id")
            or uuid.uuid4().hex
        )
        request.state.request_id = request_id
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
        if settings.access_log_json:
            access_logger.info(
                json.dumps(
                    {
                        "request_id": request_id,
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
