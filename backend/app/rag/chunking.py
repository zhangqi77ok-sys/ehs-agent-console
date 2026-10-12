"""Split regulation markdown into overlapping chunks for retrieval."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Chunk:
    chunk_id: str
    source: str
    heading: str
    text: str
    start_char: int
    end_char: int

    def to_dict(self) -> dict:
        return asdict(self)


def _heading_of(block: str) -> str:
    first = block.strip().splitlines()[0] if block.strip() else ""
    m = re.match(r"^#{1,3}\s+(.+)$", first)
    return (m.group(1).strip() if m else first[:40]) or "正文"


def chunk_markdown(
    text: str,
    *,
    source: str = "ehs_regs.md",
    max_chars: int = 280,
    overlap: int = 60,
) -> list[Chunk]:
    """Split on ## headings first, then window long sections with overlap."""
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []

    # Keep leading title out of body chunks when present
    body = text
    if body.startswith("# "):
        nl = body.find("\n")
        body = body[nl + 1 :].lstrip() if nl >= 0 else ""

    sections: list[tuple[str, str]] = []
    parts = re.split(r"(?m)^(?=##\s)", body)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        sections.append((_heading_of(part), part))

    if not sections:
        sections = [("正文", body)]

    chunks: list[Chunk] = []
    cursor = 0
    for heading, section in sections:
        # Locate approximate offset in original text for traceability
        idx = text.find(section)
        base = idx if idx >= 0 else cursor
        if len(section) <= max_chars:
            windows = [(0, len(section))]
        else:
            windows = []
            start = 0
            step = max(1, max_chars - overlap)
            while start < len(section):
                end = min(len(section), start + max_chars)
                windows.append((start, end))
                if end >= len(section):
                    break
                start += step

        for wi, (a, b) in enumerate(windows):
            piece = section[a:b].strip()
            if not piece:
                continue
            raw_id = f"{source}|{heading}|{a}|{b}|{wi}"
            cid = hashlib.sha1(raw_id.encode("utf-8")).hexdigest()[:12]
            chunks.append(
                Chunk(
                    chunk_id=cid,
                    source=source,
                    heading=heading,
                    text=piece,
                    start_char=base + a,
                    end_char=base + b,
                )
            )
        cursor = base + len(section)

    return chunks


def load_and_chunk(path: Path, **kwargs) -> list[Chunk]:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    return chunk_markdown(text, source=path.name, **kwargs)
