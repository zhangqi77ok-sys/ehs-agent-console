"""Ch18: optional OTLP HTTP JSON exporter."""

from __future__ import annotations

from app.obs.otlp import export_spans_otlp, resolve_otlp_traces_url, spans_to_otlp_json
import app.config as config_mod
from app.config import Settings


def test_otlp_noop_when_endpoint_unset():
    config_mod.settings = Settings(otel_exporter_otlp_endpoint="")
    spans = [{"span_id": "s1", "kind": "tool", "name": "list_open_hazards", "status": "ok", "step_index": 1}]
    out = export_spans_otlp(spans, run_id="run_abc")
    assert out["exported"] is False
    assert "unset" in out["reason"]
    assert out["payload"]["resourceSpans"]


def test_otlp_mock_sink_captures_payload():
    config_mod.settings = Settings(otel_exporter_otlp_endpoint="http://collector.example:4318")
    captured: list[dict] = []

    class FakeResp:
        status_code = 200

    def fake_post(url, payload, headers):
        captured.append({"url": url, "payload": payload, "headers": headers})
        return FakeResp()

    spans = [
        {
            "span_id": "span_aaa",
            "parent_span_id": None,
            "kind": "run",
            "name": "agent_loop",
            "status": "ok",
            "step_index": 0,
            "duration_ms": 12,
        },
        {
            "span_id": "span_bbb",
            "parent_span_id": "span_aaa",
            "kind": "tool",
            "name": "query_hazard_ledger",
            "status": "ok",
            "step_index": 1,
            "duration_ms": 5,
        },
    ]
    out = export_spans_otlp(spans, run_id="run_xyz", http_post=fake_post)
    assert out["exported"] is True
    assert out["http_status"] == 200
    assert out["endpoint"].endswith("/v1/traces")
    assert len(captured) == 1
    body = captured[0]["payload"]
    otlp_spans = body["resourceSpans"][0]["scopeSpans"][0]["spans"]
    assert len(otlp_spans) == 2
    assert any(s["name"] == "query_hazard_ledger" for s in otlp_spans)


def test_spans_to_otlp_json_shape():
    payload = spans_to_otlp_json(
        [{"span_id": "x", "kind": "note", "name": "n", "status": "error", "step_index": 0}],
        run_id="r1",
    )
    span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    assert span["status"]["code"] == 2
    assert resolve_otlp_traces_url("http://localhost:4318") == "http://localhost:4318/v1/traces"
    assert resolve_otlp_traces_url("http://localhost:4318/v1/traces") == "http://localhost:4318/v1/traces"


def test_export_endpoint_otlp_format(client, eng_headers, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    config_mod.settings = Settings(
        database_url=str(config_mod.settings.database_url),
        llm_provider="mock",
        hitl_enabled=False,
    )
    started = client.post(
        "/api/runs",
        headers=eng_headers,
        json={"message": "查一下灭火器相关隐患"},
    )
    assert started.status_code == 200, started.text
    run_id = started.json()["run_id"]
    exp = client.get(f"/api/runs/{run_id}/spans/export?format=otlp", headers=eng_headers)
    assert exp.status_code == 200
    body = exp.json()
    assert "resourceSpans" in body


def test_push_otlp_noop(client, eng_headers, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    config_mod.settings = Settings(
        database_url=str(config_mod.settings.database_url),
        llm_provider="mock",
        hitl_enabled=False,
        otel_exporter_otlp_endpoint="",
    )
    started = client.post(
        "/api/runs",
        headers=eng_headers,
        json={"message": "查一下灭火器相关隐患"},
    )
    run_id = started.json()["run_id"]
    r = client.post(f"/api/runs/{run_id}/spans/otlp", headers=eng_headers)
    assert r.status_code == 200
    assert r.json()["exported"] is False
