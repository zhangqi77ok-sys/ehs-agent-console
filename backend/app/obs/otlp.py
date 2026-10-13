"""Optional OTLP HTTP JSON span exporter (Ch18).

When OTEL_EXPORTER_OTLP_ENDPOINT is unset, export is a no-op.
Uses OTLP/HTTP JSON (not protobuf) so tests can capture payloads without
a collector. Not a full OpenTelemetry SDK — intentional lite surface.
"""

from __future__ import annotations

import time
from typing import Any, Callable
from urllib.parse import urljoin

import httpx

import app.config as config_mod

HttpPost = Callable[[str, dict[str, Any], dict[str, str]], Any]


def spans_to_otlp_json(
    spans: list[dict[str, Any]],
    *,
    service_name: str = "ehs-agent-console",
    run_id: str = "",
) -> dict[str, Any]:
    """Map internal AgentSpan dicts → OTLP ExportTraceServiceRequest JSON."""
    now_ns = int(time.time() * 1_000_000_000)
    otlp_spans: list[dict[str, Any]] = []
    for s in spans:
        duration_ms = int(s.get("duration_ms") or 0)
        start = now_ns
        end = now_ns + max(duration_ms, 0) * 1_000_000
        status_code = 1  # STATUS_CODE_OK
        st = str(s.get("status") or "ok")
        if st in {"error", "denied", "timeout"}:
            status_code = 2  # STATUS_CODE_ERROR
        attrs = [
            {"key": "ehs.span.kind", "value": {"stringValue": str(s.get("kind") or "")}},
            {"key": "ehs.span.name", "value": {"stringValue": str(s.get("name") or "")}},
            {"key": "ehs.step_index", "value": {"intValue": str(int(s.get("step_index") or 0))}},
        ]
        if run_id:
            attrs.append({"key": "ehs.run_id", "value": {"stringValue": run_id}})
        otlp_spans.append(
            {
                "traceId": (run_id or "trace").encode("utf-8").hex()[:32].ljust(32, "0"),
                "spanId": str(s.get("span_id") or "span").encode("utf-8").hex()[:16].ljust(16, "0"),
                "parentSpanId": (
                    str(s.get("parent_span_id") or "").encode("utf-8").hex()[:16].ljust(16, "0")
                    if s.get("parent_span_id")
                    else ""
                ),
                "name": str(s.get("name") or s.get("kind") or "span"),
                "kind": 1,
                "startTimeUnixNano": str(start),
                "endTimeUnixNano": str(end),
                "attributes": attrs,
                "status": {"code": status_code, "message": st},
            }
        )
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": service_name}},
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "ehs.agent", "version": "ch18"},
                        "spans": otlp_spans,
                    }
                ],
            }
        ]
    }


def _default_post(url: str, payload: dict[str, Any], headers: dict[str, str]) -> httpx.Response:
    with httpx.Client(timeout=10.0) as client:
        return client.post(url, json=payload, headers=headers)


def resolve_otlp_traces_url(endpoint: str | None = None) -> str | None:
    ep = (endpoint if endpoint is not None else config_mod.settings.otel_exporter_otlp_endpoint or "").strip()
    if not ep:
        return None
    if ep.rstrip("/").endswith("/v1/traces"):
        return ep
    return urljoin(ep.rstrip("/") + "/", "v1/traces")


def export_spans_otlp(
    spans: list[dict[str, Any]],
    *,
    run_id: str = "",
    endpoint: str | None = None,
    http_post: HttpPost | None = None,
) -> dict[str, Any]:
    """POST spans as OTLP HTTP JSON. No-op when endpoint unset.

    ``http_post(url, payload, headers)`` is injectable for tests (mock sink).
    """
    url = resolve_otlp_traces_url(endpoint)
    payload = spans_to_otlp_json(spans, run_id=run_id)
    if not url:
        return {
            "exported": False,
            "reason": "OTEL_EXPORTER_OTLP_ENDPOINT unset",
            "span_count": len(spans),
            "payload": payload,
        }
    headers = {"Content-Type": "application/json"}
    post = http_post or _default_post
    resp = post(url, payload, headers)
    status = getattr(resp, "status_code", None)
    if status is None and isinstance(resp, dict):
        status = resp.get("status_code", 200)
    return {
        "exported": True,
        "endpoint": url,
        "span_count": len(spans),
        "http_status": status,
        "payload": payload,
    }
