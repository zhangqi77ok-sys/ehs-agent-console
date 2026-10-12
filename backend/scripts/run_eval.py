#!/usr/bin/env python3
"""Week1 Day5 — lightweight eval harness for the EHS Agent console.

Runs 3–5 fixed cases against the real Agent loop (same path as the UI),
checks tool names + reply keywords, prints a pass/fail table.

Usage (from repo root or backend/):

    cd backend
    source .venv/bin/activate
    python scripts/run_eval.py

Exit code 0 = all passed; non-zero = at least one failure or config error.

Requires real LLM config in backend/.env (LLM_PROVIDER=openai + key/base/model).
Do not commit secrets.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

# Allow `python scripts/run_eval.py` from backend/
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.agent.loop import run_agent  # noqa: E402
from app.agent.llm import LLMConfigError  # noqa: E402
from app.config import settings  # noqa: E402

_DEFAULT_CASES = Path(__file__).resolve().parent.parent / "eval" / "cases.json"


def _load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise SystemExit(f"cases file must be a non-empty JSON array: {path}")
    return data


def _tools_called(steps: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for s in steps:
        if s.get("kind") == "tool_call" and s.get("name"):
            names.append(str(s["name"]))
    return names


def _has_final(steps: list[dict[str, Any]], reply: str) -> bool:
    if any(s.get("kind") == "final" for s in steps):
        return True
    return bool((reply or "").strip())


def _looks_like_failure(reply: str, steps: list[dict[str, Any]]) -> bool:
    text = reply or ""
    if text.startswith("调用失败：") or "已达到最大步数预算" in text:
        return True
    for s in steps:
        if s.get("kind") == "final" and str(s.get("content") or "").startswith("调用失败："):
            return True
    return False


def _check_case(case: dict[str, Any], result: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return (passed, list of failure reasons)."""
    expect = case.get("expect") or {}
    steps = result.get("steps") or []
    reply = result.get("reply") or ""
    tools = _tools_called(steps)
    reasons: list[str] = []

    required = expect.get("tools_required") or []
    for name in required:
        if name not in tools:
            reasons.append(f"缺少工具 {name}（实际: {tools or '无'}）")

    any_tools = expect.get("tools_any") or []
    if any_tools and not any(t in tools for t in any_tools):
        reasons.append(f"未调用 tools_any 中任一工具 {any_tools}（实际: {tools or '无'}）")

    kw_any = expect.get("reply_keywords_any") or []
    if kw_any and not any(k in reply for k in kw_any):
        reasons.append(f"最终回答未含关键词任一 {kw_any}")

    kw_all = expect.get("reply_keywords_all") or []
    for k in kw_all:
        if k not in reply:
            reasons.append(f"最终回答缺少关键词「{k}」")

    if expect.get("must_have_final", True) and not _has_final(steps, reply):
        reasons.append("没有 final 步骤 / 空回复")

    if expect.get("must_succeed", True) and _looks_like_failure(reply, steps):
        reasons.append(f"判定为失败回复: {reply[:120]}")

    return (len(reasons) == 0, reasons)


def _print_table(rows: list[dict[str, Any]]) -> None:
    # Simple fixed-width table — no deps.
    cols = ["id", "name", "pass", "tools", "ms", "detail"]
    widths = {c: len(c) for c in cols}
    for r in rows:
        for c in cols:
            widths[c] = max(widths[c], len(str(r.get(c, ""))))

    def fmt(r: dict[str, Any]) -> str:
        return " | ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols)

    header = {c: c for c in cols}
    sep = "-+-".join("-" * widths[c] for c in cols)
    print(fmt(header))
    print(sep)
    for r in rows:
        print(fmt(r))


async def _run_one(case: dict[str, Any]) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        result = await run_agent(case["input"], history=[])
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        ok, reasons = _check_case(case, result)
        tools = _tools_called(result.get("steps") or [])
        return {
            "id": case.get("id", "?"),
            "name": case.get("name", ""),
            "pass": "PASS" if ok else "FAIL",
            "ok": ok,
            "tools": ",".join(tools) if tools else "-",
            "ms": elapsed_ms,
            "detail": "ok" if ok else "; ".join(reasons),
            "reply": (result.get("reply") or "")[:300],
        }
    except LLMConfigError as exc:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "id": case.get("id", "?"),
            "name": case.get("name", ""),
            "pass": "FAIL",
            "ok": False,
            "tools": "-",
            "ms": elapsed_ms,
            "detail": f"LLM 配置错误: {exc}",
            "reply": "",
        }
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "id": case.get("id", "?"),
            "name": case.get("name", ""),
            "pass": "FAIL",
            "ok": False,
            "tools": "-",
            "ms": elapsed_ms,
            "detail": f"{type(exc).__name__}: {exc}",
            "reply": "",
        }


async def _main_async(cases_path: Path, case_ids: list[str] | None, verbose: bool) -> int:
    provider = (settings.llm_provider or "").strip().lower()
    print(f"LLM_PROVIDER={provider}  model={settings.openai_model}")
    if provider != "openai":
        print(
            "警告: 评测默认应对真实 LLM。"
            "当前不是 openai；结果可能与线上控制台不一致。"
            "请在 backend/.env 设 LLM_PROVIDER=openai。",
            file=sys.stderr,
        )

    cases = _load_cases(cases_path)
    if case_ids:
        want = set(case_ids)
        cases = [c for c in cases if c.get("id") in want]
        if not cases:
            print(f"没有匹配的 case id: {case_ids}", file=sys.stderr)
            return 2

    print(f"cases: {cases_path} ({len(cases)} 条)\n")
    rows: list[dict[str, Any]] = []
    for case in cases:
        print(f"→ running {case.get('id')} …", flush=True)
        row = await _run_one(case)
        rows.append(row)
        if verbose and row.get("reply"):
            print(f"  reply: {row['reply'][:200]}{'…' if len(row['reply']) > 200 else ''}")

    print()
    _print_table(rows)
    passed = sum(1 for r in rows if r["ok"])
    failed = len(rows) - passed
    print(f"\n小结: {passed}/{len(rows)} PASS, {failed} FAIL")
    return 0 if failed == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="EHS Agent 评测门禁（轻量）")
    parser.add_argument(
        "--cases",
        type=Path,
        default=_DEFAULT_CASES,
        help=f"cases JSON 路径（默认 {_DEFAULT_CASES})",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="ID",
        help="只跑指定 case id（可多个）",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="打印每条 case 的 reply 摘要",
    )
    args = parser.parse_args()
    code = asyncio.run(_main_async(args.cases, args.only, args.verbose))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
