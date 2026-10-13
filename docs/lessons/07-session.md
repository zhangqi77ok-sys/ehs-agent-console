# 07 · 多轮会话一致性

## 要解决什么
服务端 `session_id` 记住最近对话，避免只靠前端 history 丢失上下文。

- `POST /api/sessions` 创建
- 聊天带 `session_id`，服务端 `sessions.append_turn`

## 跟练
1. Agent 页发「查灭火器隐患」
2. 再发「给它开整改单，措施更换灭火器」（不重复编号）
3. 顶栏应显示 session chip

## 验收
- [ ] 第二轮能继承第一轮隐患语境（或明确追问编号）
