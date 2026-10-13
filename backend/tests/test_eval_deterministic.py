"""Ind-04: deterministic mock-LLM eval always runs in CI (no OpenAI key)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from app.config import settings

_BACKEND = Path(__file__).resolve().parent.parent
_SCRIPTS = _BACKEND / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# Import helpers from the CLI harness (same checks as scripts/run_eval.py).
import run_eval as eval_harness  # noqa: E402


@pytest.fixture(autouse=True)
def _force_mock_and_no_hitl(monkeypatch):
    """Eval under mock must not pause on write tools; restore HITL after."""
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("HITL_ENABLED", "false")
    prev_provider = settings.llm_provider
    prev_hitl = settings.hitl_enabled
    settings.llm_provider = "mock"
    settings.hitl_enabled = False
    yield
    settings.llm_provider = prev_provider
    settings.hitl_enabled = prev_hitl


def test_mock_eval_all_cases_pass(repo_fresh):
    """Full cases.json must PASS under LLM_PROVIDER=mock (CI gate)."""
    code, rows = asyncio.run(eval_harness.run_eval(verbose=False))
    failed = [r for r in rows if not r["ok"]]
    assert code == 0, "eval exit non-zero:\n" + "\n".join(
        f"{r['id']}: {r['detail']}" for r in failed
    )
    assert rows, "no cases ran"
    assert all(r["ok"] for r in rows)


def test_check_case_helper_rejects_missing_tool():
    """Sanity: _check_case fails when required tool absent."""
    case = {
        "expect": {
            "tools_required": ["list_open_hazards"],
            "must_have_final": True,
            "must_succeed": True,
        }
    }
    result = {
        "reply": "hello",
        "steps": [{"kind": "final", "content": "hello"}],
        "status": "completed",
    }
    ok, reasons = eval_harness._check_case(case, result)
    assert not ok
    assert any("list_open_hazards" in r for r in reasons)
