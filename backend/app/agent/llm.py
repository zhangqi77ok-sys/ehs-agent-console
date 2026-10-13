"""LLM backends: mock keyword router (default) + optional OpenAI-compatible."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.config import settings


class LLMConfigError(RuntimeError):
    """Real LLM selected but credentials missing."""


class LLMCallError(RuntimeError):
    """LLM HTTP call failed after retries."""


_RETRYABLE = {429, 500, 502, 503, 504}


def _line(item: dict[str, Any]) -> str:
    return (
        f"- {item['id']}｜{item['title']}｜{item['level']}｜{item.get('status') or ''}｜"
        f"责任人 {item.get('owner') or ''}"
    )


def _mock_decide(
    user_message: str, history: list[dict], tool_results: list[dict]
) -> dict[str, Any]:
    """Deterministic policy for offline demos / CI (LLM_PROVIDER=mock)."""
    _ = history
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
            lines = [_line(i) for i in items]
            return {
                "type": "final",
                "content": "查询到以下隐患：\n" + "\n".join(lines) + "\n\n如需开整改单，告诉我隐患编号和整改措施即可。",
            }
        if name == "list_open_hazards":
            items = (result.get("result") or {}).get("items") or []
            if not items:
                return {"type": "final", "content": "当前没有未闭环（待整改/整改中）的隐患。"}
            lines = [_line(i) for i in items]
            return {
                "type": "final",
                "content": f"未闭环隐患共 {len(items)} 条：\n" + "\n".join(lines),
            }
        if name == "list_corrective_tickets":
            items = (result.get("result") or {}).get("items") or []
            if not items:
                return {"type": "final", "content": "没有匹配的整改单。"}
            lines = [
                f"- {t['ticket_id']}｜隐患 {t['hazard_id']}｜{t['status']}｜{t.get('measures','')[:40]}"
                for t in items
            ]
            return {"type": "final", "content": "整改单：\n" + "\n".join(lines)}
        if name == "create_corrective_ticket":
            if result.get("ok"):
                t = result["ticket"]
                return {
                    "type": "final",
                    "content": (
                        f"已开整改单 {t['ticket_id']}：针对 {t['hazard_id']}，"
                        f"措施「{t.get('measures') or ''}」，责任人 {t.get('owner') or ''}，"
                        f"状态「{t.get('status')}」。"
                    ),
                }
            return {"type": "final", "content": f"开单失败：{result.get('error', '未知错误')}"}
        if name == "advance_corrective_ticket":
            if result.get("ok"):
                t = result.get("ticket") or {}
                hz = (result.get("hazard") or {}).get("status") or ""
                return {
                    "type": "final",
                    "content": (
                        f"整改单 {t.get('ticket_id')} 已推进：状态「{t.get('status')}」"
                        + (f"；隐患「{hz}」" if hz else "")
                        + "。"
                    ),
                }
            return {"type": "final", "content": f"推进失败：{result.get('error', '未知错误')}"}
        return {
            "type": "final",
            "content": f"工具 {name} 已执行，结果：{json.dumps(result, ensure_ascii=False)[:800]}",
        }

    if any(k in user_message for k in ("有哪些待整改", "待整改的隐患", "未闭环", "开放隐患", "未关闭隐患")):
        return {"type": "tool_call", "name": "list_open_hazards", "arguments": {}}

    # Ticket ids: TK-2026-001 (Ch1) or legacy CA-001
    tk = re.search(r"TK-?(\d{4})-?(\d{3})", user_message, re.I)
    ca = re.search(r"CA-?(\d{3})", user_message, re.I)
    if (tk or ca) and any(
        k in user_message for k in ("验收", "关闭", "推进", "驳回", "开始执行", "提交验收", "开始")
    ):
        if tk:
            ticket_id = f"TK-{tk.group(1)}-{tk.group(2)}"
        else:
            ticket_id = f"CA-{ca.group(1)}"
        if "驳回" in user_message:
            action = "reject"
        elif "开始" in user_message:
            action = "start"
        elif "提交" in user_message:
            action = "submit_verify"
        else:
            action = "close"
        evidence = ""
        em = re.search(r"(?:说明|证据)[：:]\s*(.+)", user_message)
        if em:
            evidence = em.group(1).strip()
        args: dict[str, Any] = {"ticket_id": ticket_id, "action": action}
        if action in {"close", "reject"}:
            args["evidence_note"] = evidence or ("验收通过，现场复核合格" if action == "close" else "需返工")
        return {"type": "tool_call", "name": "advance_corrective_ticket", "arguments": args}

    m = re.search(r"HZ-?(\d{4})-?(\d{3})", user_message, re.I)
    if m and any(k in user_message for k in ("开整改单", "开单", "纠正", "创建整改")):
        hazard_id = f"HZ-{m.group(1)}-{m.group(2)}"
        measures = "按制度完成整改并复查"
        am = re.search(r"措施[：:]\s*([^，,。；;]+)", user_message)
        if am:
            measures = am.group(1).strip()
        owner = ""
        om = re.search(r"责任人\s*([^，,。；;\s]+)", user_message)
        if om:
            owner = om.group(1).strip()
        return {
            "type": "tool_call",
            "name": "create_corrective_ticket",
            "arguments": {
                "hazard_id": hazard_id,
                "measures": measures,
                "owner": owner,
                "due_days": 7,
            },
        }

    if any(k in user_message for k in ("整改单列表", "有哪些整改单", "查整改单")):
        return {"type": "tool_call", "name": "list_corrective_tickets", "arguments": {}}

    keyword = ""
    for token in ("灭火器", "配电", "通道", "冲压", "危化", "叉车", "气瓶", "反光镜"):
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


def _openai_messages(
    user_message: str,
    history: list[dict],
    tool_results: list[dict],
    schemas: list[dict],
) -> list[dict[str, Any]]:
    system = (
        "你是 EHS 隐患整改助手。只能通过提供的 tools 读写台账；"
        "开单/推进必须走工具，不要编造编号。简洁中文回复。"
    )
    msgs: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for h in history[-8:]:
        role = h.get("role") or "user"
        content = h.get("content") or ""
        if role in {"user", "assistant"} and content:
            msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": user_message})
    if tool_results:
        msgs.append(
            {
                "role": "system",
                "content": "最近工具结果：" + json.dumps(tool_results[-3:], ensure_ascii=False)[:4000],
            }
        )
    msgs.append(
        {
            "role": "system",
            "content": (
                "可用工具 schemas："
                + json.dumps(schemas, ensure_ascii=False)[:3000]
                + "。若需调工具，仅输出 JSON："
                '{"type":"tool_call","name":"...","arguments":{...}}；'
                '否则输出 {"type":"final","content":"..."}。'
            ),
        }
    )
    return msgs


def _parse_decision(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    # try fenced json
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            obj = json.loads(m.group(0))
            if obj.get("type") in {"tool_call", "final"}:
                return obj
        except json.JSONDecodeError:
            pass
    return {"type": "final", "content": text or "（空回复）"}


async def complete(
    user_message: str,
    history: list[dict] | None = None,
    tool_results: list[dict] | None = None,
    schemas: list[dict] | None = None,
    *,
    force_timeout: bool = False,
    on_retry=None,
) -> dict[str, Any]:
    hist = history or []
    results = tool_results or []
    schemas = schemas or []

    if settings.llm_provider == "mock":
        if force_timeout:
            raise LLMCallError("强制超时演练：mock 路径模拟 LLM HTTP 超时")
        return _mock_decide(user_message, hist, results)

    if not settings.openai_api_key:
        raise LLMConfigError("LLM_PROVIDER=openai 但未配置 OPENAI_API_KEY")

    timeout = 0.05 if force_timeout else settings.llm_timeout_s
    msgs = _openai_messages(user_message, hist, results, schemas)
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.openai_model,
        "messages": msgs,
        "temperature": 0.2,
    }
    url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    attempts = 1 + max(0, settings.llm_max_retries)
    last_err = ""
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(attempts):
            try:
                resp = await client.post(url, headers=headers, json=body)
                if resp.status_code in _RETRYABLE and attempt < attempts - 1:
                    last_err = f"HTTP {resp.status_code}"
                    if on_retry:
                        await on_retry(attempt + 1, attempts, last_err)
                    continue
                if resp.status_code >= 400:
                    raise LLMCallError(f"LLM HTTP {resp.status_code}: {resp.text[:300]}")
                data = resp.json()
                content = (
                    ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
                )
                return _parse_decision(content)
            except httpx.TimeoutException as exc:
                last_err = "timeout"
                if attempt < attempts - 1:
                    if on_retry:
                        await on_retry(attempt + 1, attempts, last_err)
                    continue
                raise LLMCallError("LLM 调用超时") from exc
            except LLMCallError:
                raise
            except Exception as exc:  # noqa: BLE001
                last_err = str(exc)
                if attempt < attempts - 1:
                    if on_retry:
                        await on_retry(attempt + 1, attempts, last_err)
                    continue
                raise LLMCallError(last_err) from exc
    raise LLMCallError(last_err or "LLM 调用失败")
