#!/usr/bin/env python3
"""Deterministic mock eval harness (Ch6).

Usage (from backend/):
  LLM_PROVIDER=mock python scripts/run_eval.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

os.environ.setdefault("LLM_PROVIDER", "mock")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agent.loop import run_agent
from app.config import Settings
import app.config as config_mod
from app.db.base import Base
from app.db import models  # noqa: F401
from app.db.seed import seed_if_empty
from app.db import session as db_session


_DEFAULT_CASES = _BACKEND / "eval" / "cases.json"


def _load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise SystemExit(f"cases file must be a non-empty JSON array: {path}")
    return data


def _tools_called(steps: list[dict[str, Any]]) -> list[str]:
    return [str(s["name"]) for s in steps if s.get("kind") == "tool_call" and s.get("name")]


def _has_final(steps: list[dict[str, Any]], reply: str) -> bool:
    if any(s.get("kind") == "final" for s in steps):
        return True
    return bool((reply or "").strip())


def _looks_like_failure(reply: str, steps: list[dict[str, Any]]) -> bool:
    text = reply or ""
    if text.startswith("调用失败：") or "已达最大步数" in text:
        return True
    if text.startswith("开单失败：") or text.startswith("推进失败："):
        return True
    return False


def _check_case(case: dict[str, Any], result: dict[str, Any]) -> tuple[bool, list[str]]:
    expect = case.get("expect") or {}
    steps = result.get("steps") or []
    reply = result.get("reply") or ""
    tools = _tools_called(steps)
    reasons: list[str] = []

    for name in expect.get("tools_required") or []:
        if name not in tools:
            reasons.append(f"缺少工具 {name}（实际: {tools or '无'}）")

    any_tools = expect.get("tools_any") or []
    if any_tools and not any(t in tools for t in any_tools):
        reasons.append(f"未调用 tools_any 中任一工具 {any_tools}（实际: {tools or '无'}）")

    if expect.get("must_have_final", True) and not _has_final(steps, reply):
        reasons.append("缺少 final 回复")

    kws = expect.get("reply_keywords_any") or []
    if kws and not any(k in reply for k in kws):
        reasons.append(f"回复未命中任一关键词 {kws}；reply={reply[:120]!r}")

    if expect.get("must_succeed", True) and _looks_like_failure(reply, steps):
        reasons.append(f"看起来失败：{reply[:160]!r}")

    if result.get("status") not in {"completed", "paused"} and expect.get("must_succeed", True):
        # awaiting_approval not expected in eval (HITL off)
        if result.get("status") != "completed":
            reasons.append(f"status={result.get('status')}")

    return (len(reasons) == 0, reasons)


def _make_session():
    url = "sqlite://"
    engine = create_engine(
        url, connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db_session.engine = engine
    db_session.SessionLocal = Session
    config_mod.settings = Settings(database_url=url, llm_provider="mock", hitl_enabled=False)
    db = Session()
    seed_if_empty(db, tenant_id="demo-plant")
    return db


async def _run_one(db, case: dict[str, Any]) -> dict[str, Any]:
    return await run_agent(
        case["input"],
        db,
        tenant_id="demo-plant",
        role="ehs_engineer",
        actor="eval",
        hitl_enabled=False,
    )


async def main_async(cases_path: Path, verbose: bool) -> int:
    cases = _load_cases(cases_path)
    db = _make_session()
    passed = 0
    failed = 0
    print(f"LLM_PROVIDER={config_mod.settings.llm_provider}  cases={len(cases)}")
    print("-" * 72)
    try:
        for case in cases:
            t0 = time.time()
            result = await _run_one(db, case)
            ok, reasons = _check_case(case, result)
            dt = time.time() - t0
            mark = "PASS" if ok else "FAIL"
            print(f"[{mark}] {case['id']:24} {dt*1000:6.0f}ms  {case.get('name','')}")
            if verbose or not ok:
                tools = _tools_called(result.get("steps") or [])
                print(f"       tools={tools}")
                print(f"       reply={(result.get('reply') or '')[:200]}")
                for r in reasons:
                    print(f"       !! {r}")
            if ok:
                passed += 1
            else:
                failed += 1
    finally:
        db.close()
    print("-" * 72)
    print(f"passed={passed} failed={failed}")
    return 0 if failed == 0 else 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=Path, default=_DEFAULT_CASES)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    raise SystemExit(asyncio.run(main_async(args.cases, args.verbose)))


if __name__ == "__main__":
    main()
