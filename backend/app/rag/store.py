"""FAISS flat IP index over L2-normalized vectors (= cosine similarity)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import faiss
import numpy as np

from .chunking import Chunk


@dataclass
class Hit:
    chunk: Chunk
    score: float
    rank: int


class FaissStore:
    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.chunks: list[Chunk] = []

    def add(self, vectors: np.ndarray, chunks: Sequence[Chunk]) -> None:
        if vectors.shape[0] != len(chunks):
            raise ValueError("vectors/chunks length mismatch")
        if vectors.dtype != np.float32:
            vectors = vectors.astype(np.float32)
        if vectors.ndim != 2 or vectors.shape[1] != self.dim:
            raise ValueError(f"expected (*, {self.dim}), got {vectors.shape}")
        self.index.add(vectors)
        self.chunks.extend(chunks)

    def search(self, query_vec: np.ndarray, top_k: int = 3) -> list[Hit]:
        if self.index.ntotal == 0:
            return []
        q = query_vec.astype(np.float32)
        if q.ndim == 1:
            q = q.reshape(1, -1)
        k = min(top_k, self.index.ntotal)
        scores, idxs = self.index.search(q, k)
        hits: list[Hit] = []
        for rank, (score, idx) in enumerate(zip(scores[0].tolist(), idxs[0].tolist(), strict=True)):
            if idx < 0:
                continue
            hits.append(Hit(chunk=self.chunks[idx], score=float(score), rank=rank + 1))
        return hits
