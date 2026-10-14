"""Ch9: regulations RAG + tool."""

from __future__ import annotations

import asyncio

from app.rag.chunk import chunk_markdown, load_markdown_dir
from app.rag.embed import cosine, embed_text
from app.rag.store import RegulationsStore, get_regulations_store
from app.tools.domain_tools import ToolContext, search_regulations


def test_embed_deterministic_and_cosine():
    a = embed_text("灭火器过期更换")
    b = embed_text("灭火器过期更换")
    c = embed_text("危化品标签模糊")
    assert a == b
    assert cosine(a, b) > 0.99
    assert cosine(a, c) < cosine(a, b)


def test_chunk_and_store_search():
    md = "## 灭火器\n过期须更换。\n\n## 其他\n无关内容。"
    chunks = chunk_markdown(md, source="t.md")
    assert len(chunks) >= 2
    store = RegulationsStore(chunks)
    hits = store.search("灭火器过期", top_k=2)
    assert hits
    assert "灭火器" in hits[0]["text"]


def test_default_store_loads_files():
    store = get_regulations_store()
    assert len(store.chunks) >= 4
    hits = store.search("配电柜堆放纸箱", top_k=3)
    assert hits
    assert any("电气" in h["source"] or "配电" in h["text"] for h in hits)


def test_search_regulations_tool(client, eng_headers):
    # use session from client app override via agent path
    from app.db.session import SessionLocal
    from app.config import settings
    import app.db.session as session_mod

    db = session_mod.SessionLocal()
    try:
        ctx = ToolContext(session=db, tenant_id="demo-plant", role="ehs_engineer", actor="eng")
        out = search_regulations(ctx, query="灭火器压力表入红区怎么处理", top_k=3)
        assert out["ok"] is True
        assert out["result"]["count"] >= 1
        assert out["result"]["hits"][0]["text"]
    finally:
        db.close()


def test_agent_calls_search_regulations(client, eng_headers, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("HITL_ENABLED", "false")
    from app.config import Settings
    import app.config as config_mod

    config_mod.settings = Settings(
        database_url=config_mod.settings.database_url,
        llm_provider="mock",
        hitl_enabled=False,
    )
    r = client.post(
        "/api/agent/chat",
        headers=eng_headers,
        json={"message": "请查制度：灭火器过期应按什么规定处理？"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    tools = [s.get("name") for s in body.get("steps") or [] if s.get("kind") == "tool_call"]
    assert "search_regulations" in tools
    assert any(k in (body.get("reply") or "") for k in ("制度", "灭火器", "消防", "片段"))


def test_tenant_filter_excludes_other_plant():
    from app.rag.store import RegulationsStore, reset_regulations_store

    reset_regulations_store()
    store = RegulationsStore.from_dir()
    demo_hits = store.search("灭火器", top_k=5, tenant_id="demo-plant")
    assert demo_hits
    assert all(h["tenant_id"] == "demo-plant" for h in demo_hits)
    other_hits = store.search("蓝色安全帽", top_k=5, tenant_id="other-plant")
    assert other_hits
    assert all(h["tenant_id"] == "other-plant" for h in other_hits)
