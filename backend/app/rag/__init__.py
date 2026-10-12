"""Week2 local vector RAG: chunk → embed → FAISS retrieve (no LangChain)."""

from .index import ensure_index, search

__all__ = ["ensure_index", "search"]
