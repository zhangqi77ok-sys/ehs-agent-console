"""LLM backends: OpenAI-compatible (default) and optional mock for offline demos."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import httpx

from ..config import settings


class LLMConfigError(RuntimeError):
    """Raised when the real LLM is selected but credentials are missing."""


class LLMCallError(RuntimeError):
    """Raised when the LLM HTTP call fails after retries (timeout / 5xx / 429)."""


# Status codes worth retrying (rate-limit + gateway / server errors).
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _mock_decide(user_message: str, history: list[dict], tool_results: list[dict]) -> dict[str, Any]:
    """Deterministic policy for offline demos (LLM_PROVIDER=mock only)."""
    msg = user_message.lower()

    # If we already have tool results, produce a final answer.
    if tool_results:
        last = tool_results[-1]
        name = last.get("name", "")
        result = last.get("result", {})
        if name == "query_hazard_ledger":
            items = (result.get("result") or {}).get("items") or []
            if not items:
                return {
                    "type": "final",
                    "content": "台账里没有匹配的隐患。你可以换个关键词，或让我按「重大」级别再查一次。",
                }
            lines = [f"- {i['id']}｜{i['title']}｜{i['level']}｜{i['status']}｜责任人 {i['owner']}" for i in items]
            return {
                "type": "final",
                "content": "查询到以下隐患：\n" + "\n".join(lines) + "\n\n如需开整改单，告诉我隐患编号和整改措施即可。",
            }
        if name == "list_open_hazards":
            items = (result.get("result") or {}).get("items") or []
            if not items:
                return {"type": "final", "content": "当前没有未闭环（待整改/整改中）的隐患。"}
            lines = [f"- {i['id']}｜{i['title']}｜{i['level']}｜{i['status']}｜责任人 {i['owner']}" for i in items]
            return {
                "type": "final",
                "content": f"未闭环隐患共 {len(items)} 条：\n" + "\n".join(lines),
            }
        if name == "create_corrective_ticket":
            inner = result.get("result") or result
            if inner.get("ok"):
                t = inner["ticket"]
                return {
                    "type": "final",
                    "content": (
                        f"已开整改单 {t['ticket_id']}：针对 {t['hazard_id']}「{t.get('hazard_title') or ''}」，"
                        f"措施「{t.get('action') or t.get('measures') or ''}」，"
                        f"责任人 {t.get('assignee') or t.get('owner') or ''}，"
                        f"期限 {t.get('due_date') or t.get('due_days') or ''}。"
                    ),
                }
            return {"type": "final", "content": f"开单失败：{inner.get('error', '未知错误')}"}
        if name == "search_regulations":
            chunks = (result.get("result") or {}).get("chunks") or []
            if not chunks:
                return {"type": "final", "content": "法规摘要里没找到相关段落，建议换「隐患」「闭环」「作业票」等关键词。"}
            body = "\n\n".join(c["text"] for c in chunks)
            return {"type": "final", "content": "根据示例法规摘要：\n\n" + body}
        return {"type": "final", "content": f"工具 {name} 已执行，结果：{json.dumps(result, ensure_ascii=False)[:800]}"}

    # First turn: pick a tool from keywords.
    if any(k in user_message for k in ("有哪些待整改", "待整改的隐患", "未闭环", "开放隐患", "未关闭隐患")):
        return {"type": "tool_call", "name": "list_open_hazards", "arguments": {}}

    if any(k in msg for k in ("法规", "闭环要求", "作业票", "分级", "期限")):
        return {
            "type": "tool_call",
            "name": "search_regulations",
            "arguments": {"query": user_message},
        }

    m = re.search(r"HZ-?(\d{4})-?(\d{3})", user_message, re.I)
    if m and any(k in msg for k in ("整改", "开单", "纠正", "处理")):
        hazard_id = f"HZ-{m.group(1)}-{m.group(2)}"
        action = "按制度完成整改并复查"
        am = re.search(r"措施[：:]\s*(.+)", user_message)
        if am:
            action = am.group(1).strip()
        return {
            "type": "tool_call",
            "name": "create_corrective_ticket",
            "arguments": {"hazard_id": hazard_id, "action": action, "assignee": "现场安全员", "due_days": 7},
        }

    # Default: query ledger
    keyword = ""
    for token in ("灭火器", "配电", "通道", "重大", "一般", "待整改", "整改中", "已闭环"):
        if token in user_message:
            keyword = token
            break
    status = ""
    level = ""
    if "待整改" in user_message:
        status = "待整改"
    elif "整改中" in user_message:
        status = "整改中"
    elif "已闭环" in user_message:
        status = "已闭环"
    if "重大" in user_message:
        level = "重大"
    elif "一般" in user_message:
        level = "一般"

    return {
        "type": "tool_call",
        "name": "query_hazard_ledger",
        "arguments": {"keyword": keyword, "status": status, "level": level},
    }


def _require_openai_config() -> None:
    missing: list[str] = []
    if not (settings.openai_api_key or "").strip():
        missing.append("OPENAI_API_KEY")
    base = (settings.openai_base_url or "").strip()
    if not base or "HOST" in base:
        missing.append("OPENAI_BASE_URL")
    if missing:
        raise LLMConfigError(
            "Real LLM is the default. Set "
            + ", ".join(missing)
            + " in backend/.env (see .env.example), "
            "or set LLM_PROVIDER=mock only for offline demos."
        )


# Drill-only: tiny timeout so a real LLM HTTP call always hits TimeoutException.
_FORCE_TIMEOUT_S = 0.05


async def complete(
    user_message: str,
    history: list[dict],
    tool_results: list[dict],
    tools_schema: list[dict],
    on_retry: Any | None = None,
    force_timeout: bool = False,
) -> dict[str, Any]:
    """Decide next action. Optional on_retry(attempt, max_attempts, reason) for SSE notes.

    force_timeout: teaching drill — use an extremely short HTTP timeout for this call only
    (still hits the real OpenAI-compatible path; does not switch to mock).
    """
    provider = (settings.llm_provider or "openai").strip().lower()
    if force_timeout and provider == "mock":
        raise LLMCallError(
            "强制超时练习需要真实 LLM。请在 backend/.env 设 LLM_PROVIDER=openai 并配置密钥。"
        )
    if provider == "mock":
        return _mock_decide(user_message, history, tool_results)
    # Default path: real OpenAI-compatible API
    _require_openai_config()
    return await _openai_decide(
        user_message,
        history,
        tool_results,
        tools_schema,
        on_retry=on_retry,
        force_timeout=force_timeout,
    )


def _backoff_seconds(attempt: int, base: float | None = None) -> float:
    """Exponential backoff: base * 2^attempt, capped."""
    b = max(0.05, float(settings.llm_retry_backoff_s if base is None else base))
    return min(b * (2**attempt), 20.0)


async def _post_chat_completions(
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout_s: float | None = None,
) -> dict[str, Any]:
    """Single HTTP attempt with configured (or overridden) timeout. Raises for retryable / hard failures."""
    effective = settings.llm_timeout_s if timeout_s is None else timeout_s
    timeout = httpx.Timeout(effective)
    async with httpx.AsyncClient(
        base_url=settings.openai_base_url.rstrip("/"),
        timeout=timeout,
    ) as client:
        resp = await client.post("/chat/completions", json=payload, headers=headers)
        if resp.status_code in _RETRYABLE_STATUS:
            raise httpx.HTTPStatusError(
                f"retryable HTTP {resp.status_code}",
                request=resp.request,
                response=resp,
            )
        resp.raise_for_status()
        return resp.json()


async def _openai_decide(
    user_message: str,
    history: list[dict],
    tool_results: list[dict],
    tools_schema: list[dict],
    on_retry: Any | None = None,
    force_timeout: bool = False,
) -> dict[str, Any]:
    """Minimal OpenAI-compatible tool-calling loop step, with timeout + retries."""
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "你是 EHS 隐患闭环助手。可用工具："
                "query_hazard_ledger（按关键词/状态/级别/车间/类别/是否逾期查台账）、"
                "list_open_hazards（未闭环清单，重大与逾期优先）、"
                "create_corrective_ticket（开整改单；已闭环或已有未关闭单会失败）、"
                "list_corrective_tickets（查整改单）、"
                "advance_corrective_ticket（推进：start/submit_verify/close/reject）、"
                "search_regulations（向量检索法规/双重预防/作业票摘要）。"
                "问未闭环/待整改优先 list_open_hazards；问逾期用 overdue_only 或 status=逾期；"
                "开单后若用户要推进验收，用 advance_corrective_ticket；"
                "法规类必须先 search_regulations，回答点明 heading，禁止编造未检索条文。"
                "用中文简洁作答；一次只调用一个工具。"
            ),
        }
    ]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_message})
    for tr in tool_results:
        messages.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tr.get("call_id", "call_1"),
                        "type": "function",
                        "function": {
                            "name": tr["name"],
                            "arguments": json.dumps(tr.get("arguments") or {}, ensure_ascii=False),
                        },
                    }
                ],
            }
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tr.get("call_id", "call_1"),
                "content": json.dumps(tr.get("result"), ensure_ascii=False),
            }
        )

    oai_tools = [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t.get("parameters") or {"type": "object", "properties": {}},
            },
        }
        for t in tools_schema
    ]

    payload = {
        "model": settings.openai_model,
        "messages": messages,
        "tools": oai_tools,
        "tool_choice": "auto",
    }
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    max_retries = max(0, int(settings.llm_max_retries))
    max_attempts = 1 + max_retries
    last_reason = "unknown"
    # Per-request override for the frontend 「练习：强制超时」 drill.
    effective_timeout = _FORCE_TIMEOUT_S if force_timeout else float(settings.llm_timeout_s)
    # Faster backoff when drilling so the right panel shows retries without a long wait.
    backoff_base = 0.2 if force_timeout else None

    for attempt in range(max_attempts):
        try:
            data = await _post_chat_completions(payload, headers, timeout_s=effective_timeout)
            break
        except httpx.TimeoutException as exc:
            last_reason = f"timeout after {effective_timeout}s"
            if force_timeout:
                last_reason += "（练习：强制超时）"
            if attempt >= max_attempts - 1:
                raise LLMCallError(
                    f"LLM 调用失败（已重试 {max_retries} 次）：{last_reason}"
                ) from exc
            if on_retry:
                await on_retry(attempt + 1, max_attempts, last_reason)
            await asyncio.sleep(_backoff_seconds(attempt, base=backoff_base))
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code if exc.response is not None else 0
            last_reason = f"HTTP {code}"
            # 4xx (except 429) are caller/config errors — do not retry.
            if code not in _RETRYABLE_STATUS:
                raise LLMCallError(f"LLM 调用失败：{last_reason}") from exc
            if attempt >= max_attempts - 1:
                raise LLMCallError(
                    f"LLM 调用失败（已重试 {max_retries} 次）：{last_reason}"
                ) from exc
            if on_retry:
                await on_retry(attempt + 1, max_attempts, last_reason)
            await asyncio.sleep(_backoff_seconds(attempt, base=backoff_base))
        except httpx.TransportError as exc:
            last_reason = f"transport: {exc.__class__.__name__}"
            if attempt >= max_attempts - 1:
                raise LLMCallError(
                    f"LLM 调用失败（已重试 {max_retries} 次）：{last_reason}"
                ) from exc
            if on_retry:
                await on_retry(attempt + 1, max_attempts, last_reason)
            await asyncio.sleep(_backoff_seconds(attempt, base=backoff_base))
    else:
        raise LLMCallError(f"LLM 调用失败（已重试 {max_retries} 次）：{last_reason}")

    choice = data["choices"][0]["message"]
    tool_calls = choice.get("tool_calls") or []
    if tool_calls:
        tc = tool_calls[0]
        fn = tc["function"]
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        return {
            "type": "tool_call",
            "name": fn["name"],
            "arguments": args,
            "call_id": tc.get("id", "call_1"),
        }
    return {"type": "final", "content": choice.get("content") or "（模型未返回文本）"}
