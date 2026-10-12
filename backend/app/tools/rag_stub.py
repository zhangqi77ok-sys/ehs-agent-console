"""search_regulations — Week2 vector RAG (FAISS); kept module name for stable imports."""

from __future__ import annotations

from ..rag.index import search as rag_search


def search_regulations(query: str, top_k: int = 3) -> dict:
    """Retrieve regulation chunks via local vector RAG (gateway embed → TF-IDF fallback)."""
    return rag_search(query, top_k=top_k)
