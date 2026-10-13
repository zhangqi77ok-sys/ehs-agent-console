"""Real-LLM eval path: skip without a key (Eng-02). Mock gate lives in test_eval_deterministic."""

from __future__ import annotations

import os

import pytest

from app.config import settings


def test_real_llm_eval_skipped_without_key():
    """Burning tokens stays local/manual; CI uses mock eval instead."""
    key = (os.environ.get("OPENAI_API_KEY") or settings.openai_api_key or "").strip()
    provider = (os.environ.get("LLM_PROVIDER") or settings.llm_provider or "").strip().lower()
    if provider == "mock" or not key or key.startswith("sk-your-"):
        pytest.skip("无真实 LLM key：跳过真模型 eval（确定性门禁见 test_eval_deterministic）")
    # With a real key present, only assert the cases file exists (don't burn tokens in CI).
    from pathlib import Path

    cases = Path(__file__).resolve().parent.parent / "eval" / "cases.json"
    assert cases.is_file()
