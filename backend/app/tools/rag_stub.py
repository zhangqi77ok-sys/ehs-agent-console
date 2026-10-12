"""Tiny keyword RAG over sample 法规 markdown — no vector DB in v0."""

from __future__ import annotations

from pathlib import Path

_DATA = Path(__file__).resolve().parent.parent / "data" / "ehs_regs.md"

_KEYWORDS = (
    "重大隐患",
    "一般隐患",
    "闭环",
    "整改",
    "台账",
    "作业票",
    "分级",
    "高处",
    "有限空间",
    "动火",
    "隐患",
    "法规",
)


def search_regulations(query: str, top_k: int = 3) -> dict:
    text = _DATA.read_text(encoding="utf-8") if _DATA.exists() else ""
    q = (query or "").strip()
    if not q or not text:
        return {"chunks": [], "note": "无匹配或法规文件缺失"}

    # Split on ## headings so each section is a chunk
    raw_parts = [p.strip() for p in text.split("##") if p.strip()]
    paragraphs: list[str] = []
    for p in raw_parts:
        if p.startswith("# "):
            # title-only block from leading # line — skip bare title if no body
            continue
        paragraphs.append("## " + p if not p.startswith("#") else p)

    tokens = [k for k in _KEYWORDS if k in q]
    if not tokens:
        for i in range(len(q)):
            for length in (4, 3, 2):
                if i + length <= len(q):
                    frag = q[i : i + length]
                    if frag in text and frag not in tokens:
                        tokens.append(frag)
        tokens = tokens[:6] or [q]

    scored: list[tuple[int, str]] = []
    for p in paragraphs:
        score = sum(1 for t in tokens if t in p)
        if score:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    chunks = [{"score": s, "text": t} for s, t in scored[:top_k]]
    return {"chunks": chunks, "source": str(_DATA.name), "matched_tokens": tokens}
