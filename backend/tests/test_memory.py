"""Ch10: session memory + context compression."""

from __future__ import annotations

from app.memory.compress import compress_history, estimate_chars, mock_summarize


def test_compress_triggers_on_long_history():
    hist = [{"role": "user", "content": ("隐患问题讨论" * 40)} for _ in range(10)]
    hist += [{"role": "assistant", "content": ("回复内容" * 40)} for _ in range(10)]
    assert estimate_chars(hist) > 500
    out, meta = compress_history(hist, max_chars=500, keep_recent=4)
    assert meta["compressed"] is True
    assert meta["final_chars"] <= meta["original_chars"]
    assert out[0].get("compressed") is True
    assert "历史摘要" in out[0]["content"]
    assert len(out) < len(hist)


def test_compress_noop_when_short():
    hist = [{"role": "user", "content": "查灭火器"}, {"role": "assistant", "content": "好的"}]
    out, meta = compress_history(hist, max_chars=2000, keep_recent=4)
    assert meta["compressed"] is False
    assert out == hist


def test_long_history_agent_still_completes(client, eng_headers, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    from app.config import Settings
    import app.config as config_mod

    config_mod.settings = Settings(
        database_url=config_mod.settings.database_url,
        llm_provider="mock",
        hitl_enabled=False,
        memory_max_chars=400,
        memory_keep_recent=2,
    )
    # seed session with long history via multiple turns
    session_id = None
    for i in range(6):
        payload = {
            "message": f"第{i}轮闲聊：关于消防通道堆放的讨论" + ("补充背景" * 30),
        }
        if session_id:
            payload["session_id"] = session_id
        r = client.post("/api/agent/chat", headers=eng_headers, json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        session_id = body.get("session_id")
        assert session_id, body
        assert body.get("reply")

    # final actionable turn must still work under compression
    r = client.post(
        "/api/agent/chat",
        headers=eng_headers,
        json={"message": "查一下灭火器相关隐患", "session_id": session_id},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("memory", {}).get("compressed") is True
    tools = [s.get("name") for s in body.get("steps") or [] if s.get("kind") == "tool_call"]
    assert "query_hazard_ledger" in tools
    assert "灭火器" in (body.get("reply") or "") or "HZ-2026-001" in (body.get("reply") or "")


def test_mock_summarize_stable():
    msgs = [{"role": "user", "content": "A"}, {"role": "assistant", "content": "B"}]
    assert mock_summarize(msgs) == mock_summarize(msgs)
