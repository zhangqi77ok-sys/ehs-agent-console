"""Ch16 multi-dimension eval gate."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_eval_all_dimensions_pass(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("HITL_ENABLED", "false")

    spec = importlib.util.spec_from_file_location(
        "run_eval_ch16", ROOT / "scripts" / "run_eval.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    code = asyncio.run(mod.main_async(ROOT / "eval" / "cases.json", verbose=True))
    assert code == 0
    last = ROOT / "eval" / "last_result.json"
    assert last.exists()
    import json
    payload = json.loads(last.read_text(encoding="utf-8"))
    assert payload["failed"] == 0
    for case in payload["cases"]:
        dims = case["dimensions"]
        assert dims["tool_correct"] is True
        assert dims["reply_quality"] is True
        assert dims["latency_ms"] is True
        assert dims["policy_deny"] is True


def test_eval_last_endpoint(client, eng_headers, monkeypatch):
    # ensure file exists from previous test or create stub
    last = ROOT / "eval" / "last_result.json"
    if not last.exists():
        last.write_text(
            '{"ts":"x","passed":0,"failed":0,"cases":[]}', encoding="utf-8"
        )
    r = client.get("/api/eval/last", headers=eng_headers)
    assert r.status_code == 200
    assert r.json()["available"] is True
