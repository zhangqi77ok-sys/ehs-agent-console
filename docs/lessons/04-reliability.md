# 04 · 超时 / 重试 / 预算熔断

## 要解决什么
网关偶发超时不能直接炸；步数要有预算。

## 关键点
- `LLM_TIMEOUT_S` / `LLM_MAX_RETRIES` / `TOOL_TIMEOUT_S` / `MAX_AGENT_STEPS`
- 前端勾选「练习：强制超时」→ `force_timeout=true`

## 跟练
勾选强制超时发一句，右栏见 `force_timeout_drill` 与 `llm_retry`。

## 验收
- [ ] 强制超时能看到重试 note
- [ ] 正常关闭后恢复可用
