#!/usr/bin/env python3
"""Deterministic mock eval harness (Ch6 + Ch16 multi-dimension).

Usage (from backend/):
  LLM_PROVIDER=mock python scripts/run_eval.py -v
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
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
_LAST_RESULT = _BACKEND / "eval" / "last_result.json"
_DASHBOARD = _BACKEND.parent / "docs" / "eval-dashboard.md"


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


def _had_deny(steps: list[dict[str, Any]]) -> bool:
    for s in steps:
        if s.get("kind") != "tool_result":
            continue
        res = s.get("result") or {}
        if isinstance(res, dict) and res.get("denied"):
            return True
    return False


def _check_dimensions(
    case: dict[str, Any], result: dict[str, Any], latency_ms: float
) -> dict[str, Any]:
    """Return per-dimension pass/fail for Ch16."""
    expect = case.get("expect") or {}
    dims_cfg = expect.get("dimensions") or {}
    steps = result.get("steps") or []
    reply = result.get("reply") or ""
    tools = _tools_called(steps)

    # tool_correct
    tool_ok = True
    for name in expect.get("tools_required") or []:
        if name not in tools:
            tool_ok = False
    any_tools = expect.get("tools_any") or []
    if any_tools and not any(t in tools for t in any_tools):
        tool_ok = False
    if dims_cfg.get("tool_correct") is False:
        tool_ok = True  # dimension not required

    # reply_quality (keywords)
    kws = expect.get("reply_keywords_any") or []
    reply_ok = True
    if dims_cfg.get("reply_quality", True) and kws:
        reply_ok = any(k in reply for k in kws)
    elif dims_cfg.get("reply_quality") is False:
        reply_ok = True

    # latency
    budget = float(dims_cfg.get("latency_ms_max") or 30000)
    latency_ok = latency_ms <= budget

    # policy_deny
    want_deny = bool(dims_cfg.get("policy_deny_expected"))
    denied = _had_deny(steps)
    # also treat explicit deny in reply
    if "只读" in reply or "禁止写" in reply or "无权" in reply:
        denied = True
    policy_ok = (denied == want_deny) if "policy_deny_expected" in dims_cfg else True

    # legacy overall checks still contribute to "overall"
    reasons: list[str] = []
    if expect.get("must_have_final", True) and not _has_final(steps, reply):
        reasons.append("缺少 final 回复")
    if expect.get("must_succeed", True) and _looks_like_failure(reply, steps):
        reasons.append(f"看起来失败：{reply[:160]!r}")
    if expect.get("must_succeed", True) and result.get("status") not in {"completed", "paused"}:
        if result.get("status") != "completed":
            # for deny cases must_succeed is False
            reasons.append(f"status={result.get('status')}")
    if not expect.get("must_succeed", True):
        # expect failure / deny path: overall ok if policy ok
        pass

    dims = {
        "tool_correct": tool_ok,
        "reply_quality": reply_ok,
        "latency_ms": latency_ok,
        "policy_deny": policy_ok,
        "latency_ms_value": round(latency_ms, 1),
        "latency_ms_max": budget,
    }
    all_dims = all(dims[k] for k in ("tool_correct", "reply_quality", "latency_ms", "policy_deny"))

    if not tool_ok:
        reasons.append(f"tool_correct 失败 tools={tools}")
    if not reply_ok:
        reasons.append(f"reply_quality 失败 reply={reply[:120]!r}")
    if not latency_ok:
        reasons.append(f"latency {latency_ms:.0f}ms > {budget}")
    if not policy_ok:
        reasons.append(f"policy_deny 期望={want_deny} 实际 denied={denied}")

    # For must_succeed False (deny case), overall = dims only
    if expect.get("must_succeed", True):
        overall = all_dims and len([r for r in reasons if not r.startswith("tool_") and "reply_quality" not in r and "latency" not in r and "policy_deny" not in r]) == 0
        # simpler: overall = all_dims and no legacy failure reasons beyond dims
        overall = all_dims
        if expect.get("must_have_final", True) and not _has_final(steps, reply):
            overall = False
        if _looks_like_failure(reply, steps):
            overall = False
    else:
        overall = all_dims

    return {"ok": overall, "dimensions": dims, "reasons": reasons, "tools": tools, "reply": reply}


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
    role = case.get("role") or "ehs_engineer"
    return await run_agent(
        case["input"],
        db,
        tenant_id="demo-plant",
        role=role,
        actor="eval",
        hitl_enabled=False,
    )


def _write_outputs(rows: list[dict[str, Any]], passed: int, failed: int) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "failed": failed,
        "cases": rows,
    }
    _LAST_RESULT.parent.mkdir(parents=True, exist_ok=True)
    _LAST_RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Eval Dashboard（Ch16 多维）",
        "",
        f"生成时间（UTC）：`{payload['ts']}`",
        "",
        f"**passed={passed} failed={failed}**",
        "",
        "| case | tool_correct | reply_quality | latency | policy_deny | overall | ms |",
        "|------|--------------|---------------|---------|-------------|---------|----|",
    ]
    for r in rows:
        d = r["dimensions"]
        def mark(v):
            return "✅" if v else "❌"
        lines.append(
            f"| {r['id']} | {mark(d['tool_correct'])} | {mark(d['reply_quality'])} | "
            f"{mark(d['latency_ms'])} | {mark(d['policy_deny'])} | "
            f"{'PASS' if r['ok'] else 'FAIL'} | {d['latency_ms_value']} |"
        )
    lines.append("")
    lines.append("重新生成：`cd backend && LLM_PROVIDER=mock python scripts/run_eval.py`")
    lines.append("")
    _DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
    _DASHBOARD.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def main_async(cases_path: Path, verbose: bool) -> int:
    cases = _load_cases(cases_path)
    db = _make_session()
    passed = 0
    failed = 0
    rows: list[dict[str, Any]] = []
    print(f"LLM_PROVIDER={config_mod.settings.llm_provider}  cases={len(cases)}  (Ch16 dims)")
    print("-" * 88)
    print(f"{'case':28} {'tool':5} {'reply':5} {'lat':5} {'deny':5} {'ms':7} result")
    print("-" * 88)
    try:
        for case in cases:
            t0 = time.time()
            result = await _run_one(db, case)
            dt = (time.time() - t0) * 1000
            checked = _check_dimensions(case, result, dt)
            ok = checked["ok"]
            d = checked["dimensions"]
            mark = "PASS" if ok else "FAIL"
            def yn(v):
                return "Y" if v else "N"
            print(
                f"[{mark}] {case['id']:24} {yn(d['tool_correct']):5} {yn(d['reply_quality']):5} "
                f"{yn(d['latency_ms']):5} {yn(d['policy_deny']):5} {dt:7.0f}  {case.get('name','')}"
            )
            if verbose or not ok:
                print(f"       tools={checked['tools']}")
                print(f"       reply={(checked['reply'] or '')[:200]}")
                for r in checked["reasons"]:
                    print(f"       !! {r}")
            rows.append({"id": case["id"], "name": case.get("name", ""), "ok": ok, "dimensions": d, "reasons": checked["reasons"]})
            if ok:
                passed += 1
            else:
                failed += 1
    finally:
        db.close()
    print("-" * 88)
    print(f"passed={passed} failed={failed}")
    _write_outputs(rows, passed, failed)
    return 0 if failed == 0 else 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=Path, default=_DEFAULT_CASES)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    raise SystemExit(asyncio.run(main_async(args.cases, args.verbose)))


if __name__ == "__main__":
    main()
