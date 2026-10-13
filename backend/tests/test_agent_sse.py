"""Ch3: SSE stream of agent steps/budget."""

from __future__ import annotations


def _parse_sse(text: str) -> list[tuple[str, str]]:
    events: list[tuple[str, str]] = []
    event = "message"
    for line in text.splitlines():
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            events.append((event, line[5:].strip()))
            event = "message"
    return events


def test_sse_streams_budget_and_done(client, eng_headers):
    with client.stream(
        "POST",
        "/api/agent/chat/stream",
        headers=eng_headers,
        json={"message": "有哪些未闭环隐患？"},
    ) as res:
        assert res.status_code == 200
        assert "text/event-stream" in res.headers.get("content-type", "")
        body = "".join(res.iter_text())

    events = _parse_sse(body)
    names = [e[0] for e in events]
    assert "budget" in names
    assert "tool_call" in names or "step_start" in names
    assert "done" in names
    assert "final" in names or any("未闭环" in d or "隐患" in d for _, d in events)


def test_sse_force_timeout_drill(client, eng_headers, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    # force_timeout on mock raises LLMCallError → error + done
    with client.stream(
        "POST",
        "/api/agent/chat/stream",
        headers=eng_headers,
        json={"message": "查隐患", "force_timeout": True},
    ) as res:
        body = "".join(res.iter_text())
    names = [e[0] for e in _parse_sse(body)]
    assert "note" in names or "error" in names
    assert "done" in names
