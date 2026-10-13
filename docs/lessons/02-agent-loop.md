# 02 · 手写 Agent 循环 + 工具调用

## 要解决什么
把第 1 章领域工具接到 **手写 ReAct 循环**（`backend/app/agent/loop.py`），默认真实 LLM，不用 LangChain。

## 关键点
- `stream_agent` / `run_agent`：decide → tool → observe
- `tools/registry.py`：schema + dispatch
- 前端「Agent 控制台」页签走 `POST /api/chat`

## 跟练
1. 配好 `backend/.env` 的 `OPENAI_*`
2. 打开 **Agent 控制台**，问「有哪些重大逾期隐患？」
3. 右栏应出现 `tool_call` / `tool_result` / `final`

## 验收
- [ ] 能调用 `list_open_hazards` 或 `query_hazard_ledger`
- [ ] 回答引用真实隐患编号
