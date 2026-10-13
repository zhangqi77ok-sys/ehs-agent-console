# 03 · SSE 左聊右步骤

## 要解决什么
Agent 决策过程要**边跑边看得见**：`POST /api/chat` 发 `text/event-stream`。

## 事件
`identity` → `budget` → `step_start` → `tool_call` → `tool_result` → `final` → `done`（可穿插 `note`/`error`）

## 跟练
发一条会开工具的问题，确认右栏逐步追加，而不是等整轮结束才刷。

## 验收
- [ ] 网络面板 Content-Type 为 event-stream
- [ ] 工具结果先于最终回答出现在右栏
