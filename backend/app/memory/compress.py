"""Context compression: summarize older turns when over char budget."""

from __future__ import annotations

from typing import Any


def estimate_chars(messages: list[dict[str, Any]]) -> int:
    total = 0
    for m in messages or []:
        total += len(str(m.get("role") or "")) + len(str(m.get("content") or "")) + 8
    return total


def mock_summarize(messages: list[dict[str, Any]]) -> str:
    """Deterministic mock summarizer (no LLM required)."""
    bits: list[str] = []
    for m in messages:
        role = m.get("role") or "user"
        content = (m.get("content") or "").strip().replace("\n", " ")
        if not content:
            continue
        bits.append(f"{role}:{content[:80]}")
    joined = "；".join(bits[:12])
    return f"【历史摘要】共{len(messages)}条。" + joined[:400]


def compress_history(
    history: list[dict[str, Any]] | None,
    *,
    max_chars: int = 2000,
    keep_recent: int = 4,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """If over budget, replace older turns with one summary message."""
    hist = list(history or [])
    meta: dict[str, Any] = {
        "compressed": False,
        "original_count": len(hist),
        "original_chars": estimate_chars(hist),
        "max_chars": max_chars,
    }
    if estimate_chars(hist) <= max_chars or len(hist) <= keep_recent:
        meta["final_count"] = len(hist)
        meta["final_chars"] = meta["original_chars"]
        return hist, meta

    keep = max(1, keep_recent)
    older = hist[:-keep]
    recent = hist[-keep:]
    summary = mock_summarize(older)
    compressed = [{"role": "system", "content": summary, "compressed": True}] + recent
    while estimate_chars(compressed) > max_chars and len(compressed) > 1:
        if len(compressed) > 2:
            compressed.pop(1)
        else:
            break
    meta.update(
        {
            "compressed": True,
            "summarized_count": len(older),
            "final_count": len(compressed),
            "final_chars": estimate_chars(compressed),
            "summary_preview": summary[:120],
        }
    )
    return compressed, meta
