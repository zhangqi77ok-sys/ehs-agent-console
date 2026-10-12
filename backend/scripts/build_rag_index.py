#!/usr/bin/env python3
"""Build (or rebuild) the local FAISS RAG index for EHS regulations.

Usage:
    cd backend
    source .venv/bin/activate
    python scripts/build_rag_index.py
    python scripts/build_rag_index.py --force
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.config import settings  # noqa: E402
from app.rag.embeddings import probe_openai_embeddings  # noqa: E402
from app.rag.index import ensure_index  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build EHS regulation RAG index")
    parser.add_argument("--force", action="store_true", help="忽略已有 index.pkl，强制重建")
    args = parser.parse_args()

    model = (settings.openai_embedding_model or "").strip()
    ok, detail = probe_openai_embeddings(model) if model else (False, "OPENAI_EMBEDDING_MODEL unset")
    print(f"gateway embeddings probe: ok={ok}  {detail}")
    print(f"prefer={settings.rag_embedding_prefer}  index_dir={settings.rag_index_dir}")

    state = ensure_index(force_rebuild=args.force)
    meta_path = Path(settings.rag_index_dir) / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    print(
        f"ready: embedding={state['embedding_name']}  chunks={state['n_chunks']}  "
        f"dim={state['dim']}  source={state['source']}"
    )
    print(f"meta: {json.dumps(meta, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
