"""Embeddings: OpenAI-compatible gateway first, local TF-IDF fallback."""

from __future__ import annotations

import logging
from typing import Sequence

import httpx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from ..config import settings

logger = logging.getLogger(__name__)


def _l2_normalize(mat: np.ndarray) -> np.ndarray:
    if mat.size == 0:
        return mat.astype(np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return (mat / norms).astype(np.float32)


class Embedder:
    """Shared embedder for index build + query time."""

    name: str

    def fit(self, texts: Sequence[str]) -> None:  # noqa: ARG002
        return None

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        raise NotImplementedError


class OpenAIEmbedder(Embedder):
    """POST {OPENAI_BASE_URL}/embeddings — same key as chat."""

    name = "openai"

    def __init__(self, model: str) -> None:
        self.model = model
        self._dim: int | None = None

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self._dim or 0), dtype=np.float32)
        base = settings.openai_base_url.rstrip("/")
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model, "input": list(texts)}
        timeout = httpx.Timeout(float(settings.llm_timeout_s))
        with httpx.Client(base_url=base, timeout=timeout) as client:
            resp = client.post("/embeddings", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        items = sorted(data["data"], key=lambda x: x["index"])
        vectors = [np.asarray(it["embedding"], dtype=np.float32) for it in items]
        mat = np.vstack(vectors)
        self._dim = mat.shape[1]
        return _l2_normalize(mat)


class LocalTfidfEmbedder(Embedder):
    """Character n-gram TF-IDF — works offline, Chinese-friendly, no model download."""

    name = "local_tfidf"

    def __init__(self) -> None:
        self._vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 4),
            min_df=1,
            max_features=4096,
            sublinear_tf=True,
        )
        self._fitted = False

    def fit(self, texts: Sequence[str]) -> None:
        corpus = [t if t.strip() else " " for t in texts]
        self._vectorizer.fit(corpus)
        self._fitted = True

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("LocalTfidfEmbedder must be fit() before embed()")
        corpus = [t if t.strip() else " " for t in texts]
        mat = self._vectorizer.transform(corpus).astype(np.float32).toarray()
        return _l2_normalize(mat)


def probe_openai_embeddings(model: str | None = None) -> tuple[bool, str]:
    """Return (ok, detail). Used at index build to decide gateway vs local."""
    model = (model or settings.openai_embedding_model or "").strip()
    if not model:
        return False, "OPENAI_EMBEDDING_MODEL unset"
    key = (settings.openai_api_key or "").strip()
    base = (settings.openai_base_url or "").strip()
    if not key or not base or "HOST" in base:
        return False, "missing OPENAI_API_KEY / OPENAI_BASE_URL"
    try:
        emb = OpenAIEmbedder(model)
        vec = emb.embed(["ping"])
        return True, f"ok dim={vec.shape[1]} model={model}"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def build_embedder(corpus: Sequence[str]) -> Embedder:
    """Prefer gateway embeddings; fall back to local TF-IDF."""
    prefer = (settings.rag_embedding_prefer or "openai").strip().lower()
    model = (settings.openai_embedding_model or "").strip()

    if prefer in ("openai", "auto") and model:
        ok, detail = probe_openai_embeddings(model)
        if ok:
            logger.info("RAG embeddings: openai (%s)", detail)
            return OpenAIEmbedder(model)
        logger.warning("RAG embeddings: openai unavailable (%s); using local_tfidf", detail)
    elif prefer == "local":
        logger.info("RAG embeddings: forced local_tfidf")
    else:
        logger.info(
            "RAG embeddings: skipping openai (prefer=%s model=%r); using local_tfidf",
            prefer,
            model,
        )

    local = LocalTfidfEmbedder()
    local.fit(corpus)
    logger.info("RAG embeddings: local_tfidf (docs=%d)", len(corpus))
    return local
