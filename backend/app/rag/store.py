"""In-memory cosine store over hashed embeddings (Ch9)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.rag.chunk import load_markdown_dir
from app.rag.embed import cosine, embed_text

_DEFAULT_DIR = Path(__file__).resolve().parents[2] / "data" / "regulations"

_store: "RegulationsStore | None" = None


class RegulationsStore:
    def __init__(self, chunks: list[dict[str, Any]] | None = None, dim: int = 256):
        self.dim = dim
        self.chunks = list(chunks or [])
        self.vectors = [embed_text(c["text"], dim=dim) for c in self.chunks]

    @classmethod
    def from_dir(cls, root: Path | None = None) -> "RegulationsStore":
        root = root or _DEFAULT_DIR
        return cls(load_markdown_dir(root))

    def search(self, query: str, *, top_k: int = 3) -> list[dict[str, Any]]:
        if not self.chunks:
            return []
        q = embed_text(query, dim=self.dim)
        scored = []
        for chunk, vec in zip(self.chunks, self.vectors):
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
