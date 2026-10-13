"""Local embedding fallback: hashed bag-of-ngrams (no external API)."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter


_TOKEN = re.compile(r"[\u4e00-\u9fff]|[A-Za-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall((text or "").lower())


def embed_text(text: str, dim: int = 256) -> list[float]:
    """Deterministic hashing trick embedding + L2 normalize."""
    vec = [0.0] * dim
    toks = tokenize(text)
    if not toks:
        return vec
    # unigrams + bigrams
    grams = list(toks)
    grams += [toks[i] + toks[i + 1] for i in range(len(toks) - 1)]
    counts = Counter(grams)
    for g, c in counts.items():
        h = int(hashlib.md5(g.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) & 1 else -1.0
        vec[idx] += sign * (1.0 + math.log(1 + c))
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
