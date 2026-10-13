"""Eval gate: skip in CI / without a real LLM key (Eng-02 DoD)."""

from __future__ import annotations

import os

import pytest

from app.config import settings


def test_eval_skipped_without_real_llm_key():
    """CI stays green without secrets; full eval stays a local/manual gate."""
    key = (os.environ.get("OPENAI_API_KEY") or settings.openai_api_key or "").strip()
    provider = (os.environ.get("LLM_PROVIDER") or settings.llm_provider or "").strip().lower()
    if provider == "mock" or not key or key.startswith("sk-your-"):
        pytest.skip("无真实 LLM key：跳过 eval（本地有 key 时用 python scripts/run_eval.py）")
    # With a real key present, only assert the cases file exists (don't burn tokens in CI).
    from pathlib import Path

    cases = Path(__file__).resolve().parent.parent / "eval" / "cases.json"
    assert cases.is_file()
