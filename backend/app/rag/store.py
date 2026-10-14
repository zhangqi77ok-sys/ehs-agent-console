"""In-memory cosine store over hashed embeddings (Ch9) with tenant filter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.rag.chunk import load_all_tenant_corpora, load_markdown_dir
from app.rag.embed import cosine, embed_text

_DEFAULT_DIR = Path(__file__).resolve().parents[2] / "data" / "regulations"

_store: "RegulationsStore | None" = None


class RegulationsStore:
    def __init__(self, chunks: list[dict[str, Any]] | None = None, dim: int = 256):
        self.dim = dim
        self.chunks = list(chunks or [])
        for c in self.chunks:
            if "tenant_id" not in c or not c.get("tenant_id"):
                c["tenant_id"] = "demo-plant"
        self.vectors = [embed_text(c["text"], dim=dim) for c in self.chunks]

    @classmethod
    def from_dir(cls, root: Path | None = None) -> "RegulationsStore":
        root = root or _DEFAULT_DIR
        return cls(load_all_tenant_corpora(root))

    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self.chunks:
            return []
        tid = (tenant_id or "").strip() or None
        q = embed_text(query, dim=self.dim)
        scored = []
        for chunk, vec in zip(self.chunks, self.vectors):
            if tid and str(chunk.get("tenant_id") or "") != tid:
                continue
            score = cosine(q, vec)
            scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, chunk in scored[: max(1, top_k)]:
            out.append(
                {
                    "id": chunk["id"],
                    "source": chunk["source"],
                    "text": chunk["text"],
                    "score": round(float(score), 4),
                    "tenant_id": chunk.get("tenant_id") or "",
                }
            )
        return out


def get_regulations_store() -> RegulationsStore:
    global _store
    if _store is None:
        _store = RegulationsStore.from_dir()
    return _store


def reset_regulations_store(store: RegulationsStore | None = None) -> None:
    global _store
    _store = store
