"""Markdown chunking for regulation docs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def chunk_markdown(text: str, *, source: str, max_chars: int = 400) -> list[dict[str, Any]]:
    parts = re.split(r"\n(?=##\s)", text.strip())
    chunks: list[dict[str, Any]] = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        if len(part) <= max_chars:
            chunks.append({"id": f"{source}#{i}", "source": source, "text": part})
            continue
        # split long sections by lines
        buf = ""
        sub = 0
        for line in part.splitlines():
            if len(buf) + len(line) + 1 > max_chars and buf:
                chunks.append({"id": f"{source}#{i}.{sub}", "source": source, "text": buf.strip()})
                sub += 1
                buf = line
            else:
                buf = f"{buf}\n{line}" if buf else line
        if buf.strip():
            chunks.append({"id": f"{source}#{i}.{sub}", "source": source, "text": buf.strip()})
    return chunks


def load_markdown_dir(root: Path) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    if not root.exists():
        return chunks
    for path in sorted(root.glob("**/*.md")):
        rel = path.name
        text = path.read_text(encoding="utf-8")
        chunks.extend(chunk_markdown(text, source=rel))
    return chunks
