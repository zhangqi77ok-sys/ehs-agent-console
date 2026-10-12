"""Build / load / search the regulation RAG index (lazy singleton)."""

from __future__ import annotations

import json
import logging
import pickle
import threading
from pathlib import Path
from typing import Any

import numpy as np

from ..config import settings
from .chunking import Chunk, load_and_chunk
from .embeddings import Embedder, LocalTfidfEmbedder, OpenAIEmbedder, build_embedder
from .store import FaissStore

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_STATE: dict[str, Any] | None = None

_DEFAULT_REG = Path(__file__).resolve().parent.parent / "data" / "ehs_regs.md"


def _rag_dir() -> Path:
    return Path(settings.rag_index_dir)


def _meta_path() -> Path:
    return _rag_dir() / "meta.json"


def _blob_path() -> Path:
    return _rag_dir() / "index.pkl"


def build_index(
    regs_path: Path | None = None,
    *,
    persist: bool = True,
) -> dict[str, Any]:
    """Chunk → embed → FAISS. Returns runtime state dict."""
    path = regs_path or Path(settings.rag_regs_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent.parent / path
    if not path.exists():
        path = _DEFAULT_REG

    chunks = load_and_chunk(
        path,
        max_chars=int(settings.rag_chunk_chars),
        overlap=int(settings.rag_chunk_overlap),
    )
    if not chunks:
        raise RuntimeError(f"no chunks from {path}")

    texts = [c.text for c in chunks]
    embedder = build_embedder(texts)
    vectors = embedder.embed(texts)
    store = FaissStore(dim=vectors.shape[1])
    store.add(vectors, chunks)

    state = {
        "store": store,
        "embedder": embedder,
        "embedding_name": embedder.name,
        "embedding_model": getattr(embedder, "model", None),
        "source": path.name,
        "source_path": str(path),
        "n_chunks": len(chunks),
        "dim": int(vectors.shape[1]),
    }

    if persist:
        _persist(state, chunks, vectors)

    logger.info(
        "RAG index ready: chunks=%d dim=%d embedding=%s source=%s",
        state["n_chunks"],
        state["dim"],
        state["embedding_name"],
        state["source"],
    )
    return state


def _persist(state: dict[str, Any], chunks: list[Chunk], vectors: np.ndarray) -> None:
    d = _rag_dir()
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "chunks": [c.to_dict() for c in chunks],
        "vectors": vectors,
        "embedding_name": state["embedding_name"],
        "embedding_model": state.get("embedding_model"),
        "source": state["source"],
        "dim": state["dim"],
        "embedder": state["embedder"],  # pickle vectorizer / thin openai wrapper
    }
    _blob_path().write_bytes(pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL))
    meta = {
        "n_chunks": state["n_chunks"],
        "dim": state["dim"],
        "embedding": state["embedding_name"],
        "embedding_model": state.get("embedding_model"),
        "source": state["source"],
        "backend": "faiss",
    }
    _meta_path().write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_persisted() -> dict[str, Any] | None:
    if not _blob_path().exists():
        return None
    try:
        payload = pickle.loads(_blob_path().read_bytes())
        chunks = [Chunk(**c) for c in payload["chunks"]]
        vectors = np.asarray(payload["vectors"], dtype=np.float32)
        embedder: Embedder = payload["embedder"]
        store = FaissStore(dim=int(payload["dim"]))
        store.add(vectors, chunks)
        return {
            "store": store,
            "embedder": embedder,
            "embedding_name": payload["embedding_name"],
            "embedding_model": payload.get("embedding_model"),
            "source": payload["source"],
            "source_path": "",
            "n_chunks": len(chunks),
            "dim": int(payload["dim"]),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("failed to load RAG index pickle (%s); rebuilding", exc)
        return None


def ensure_index(*, force_rebuild: bool = False) -> dict[str, Any]:
    global _STATE
    with _LOCK:
        if _STATE is not None and not force_rebuild:
            return _STATE
        if not force_rebuild and settings.rag_load_persisted:
            loaded = _load_persisted()
            if loaded is not None:
                _STATE = loaded
                return _STATE
        _STATE = build_index(persist=True)
        return _STATE


def search(query: str, top_k: int | None = None) -> dict[str, Any]:
    """Retrieve top-k chunks; return structure suitable for tool_result / SSE."""
    q = (query or "").strip()
    k = int(top_k if top_k is not None else settings.rag_top_k)
    if not q:
        return {
            "chunks": [],
            "note": "空查询",
            "retrieval": {"backend": "faiss", "embedding": None, "top_k": k, "query": q},
        }

    state = ensure_index()
    embedder: Embedder = state["embedder"]
    store: FaissStore = state["store"]
    qvec = embedder.embed([q])[0]
    hits = store.search(qvec, top_k=k)

    chunks_out = []
    for h in hits:
        chunks_out.append(
            {
                "rank": h.rank,
                "score": round(h.score, 4),
                "text": h.chunk.text,
                "source": h.chunk.source,
                "chunk_id": h.chunk.chunk_id,
                "heading": h.chunk.heading,
            }
        )

    return {
        "chunks": chunks_out,
        "source": state["source"],
        "retrieval": {
            "backend": "faiss",
            "embedding": state["embedding_name"],
            "embedding_model": state.get("embedding_model"),
            "top_k": k,
            "query": q,
            "n_chunks_indexed": state["n_chunks"],
            "dim": state["dim"],
        },
        "cite_hint": "请在最终回答中引用 heading / chunk_id，并概括条款，勿整段照抄。",
    }
