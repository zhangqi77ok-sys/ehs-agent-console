"""Ch6: deterministic mock eval always-on in pytest."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_eval_cases_pass_under_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("HITL_ENABLED", "false")

    spec = importlib.util.spec_from_file_location(
        "run_eval", ROOT / "scripts" / "run_eval.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    code = asyncio.run(mod.main_async(ROOT / "eval" / "cases.json", verbose=False))
    assert code == 0
