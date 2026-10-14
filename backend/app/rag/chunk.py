"""Markdown chunking for regulation docs (tenant-tagged)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def chunk_markdown(
    text: str,
    *,
    source: str,
    max_chars: int = 400,
    tenant_id: str = "demo-plant",
) -> list[dict[str, Any]]:
    parts = re.split(r"\n(?=##\s)", text.strip())
    chunks: list[dict[str, Any]] = []
    tid = (tenant_id or "demo-plant").strip() or "demo-plant"
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        if len(part) <= max_chars:
            chunks.append(
                {"id": f"{tid}:{source}#{i}", "source": source, "text": part, "tenant_id": tid}
            )
            continue
        buf = ""
        sub = 0
        for line in part.splitlines():
            if len(buf) + len(line) + 1 > max_chars and buf:
                chunks.append(
                    {
                        "id": f"{tid}:{source}#{i}.{sub}",
                        "source": source,
                        "text": buf.strip(),
                        "tenant_id": tid,
                    }
                )
                sub += 1
                buf = line
            else:
                buf = f"{buf}\n{line}" if buf else line
        if buf.strip():
            chunks.append(
                {
                    "id": f"{tid}:{source}#{i}.{sub}",
                    "source": source,
                    "text": buf.strip(),
                    "tenant_id": tid,
                }
            )
    return chunks


def load_markdown_dir(root: Path, *, tenant_id: str = "demo-plant") -> list[dict[str, Any]]:
    """Load *.md under root and tag every chunk with tenant_id."""
    chunks: list[dict[str, Any]] = []
    if not root.exists():
        return chunks
    tid = (tenant_id or "demo-plant").strip() or "demo-plant"
    for path in sorted(root.glob("**/*.md")):
        # Skip nested tenant overlay dirs when loading the shared root flat.
        if path.parent != root and path.parent.name.startswith("tenant-"):
            continue
        rel = path.name
        text = path.read_text(encoding="utf-8")
        chunks.extend(chunk_markdown(text, source=rel, tenant_id=tid))
    return chunks


def load_all_tenant_corpora(root: Path) -> list[dict[str, Any]]:
    """Load shared root as demo-plant + optional tenant-<id>/ subdirs."""
    chunks = load_markdown_dir(root, tenant_id="demo-plant")
    if not root.exists():
        return chunks
    for sub in sorted(root.iterdir()):
        if sub.is_dir() and sub.name.startswith("tenant-"):
            tid = sub.name[len("tenant-") :] or "demo-plant"
            for path in sorted(sub.glob("**/*.md")):
                text = path.read_text(encoding="utf-8")
                chunks.extend(chunk_markdown(text, source=path.name, tenant_id=tid))
    return chunks
