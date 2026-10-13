# Ch3 课记：SSE 推送 Agent 步骤

## 为什么要 SSE

JSON 一次性返回适合测试；演示与排障需要**边跑边看** tool_call / budget / final。  
`POST /api/agent/chat/stream` 用 `text/event-stream` 推送与循环内相同的事件名：

`identity` → `budget` → `step_start` → `tool_call` → `tool_result` → `final` → `done`  
（失败有 `error`；暂停有 `paused`）

## 前端怎么接

Agent 页勾选 **SSE**：`fetch` + `ReadableStream` 解析 `event:` / `data:` 行（比 EventSource 更易带自定义头 `X-Tenant-Id`）。  
每来一个 step 就刷新右侧面板——面试可讲「观察性比最终答案更重要」。

## 强制超时演练

勾选 **强制超时**：mock 路径直接抛「强制超时演练」；openai 路径把 HTTP timeout 压到 ~50ms。  
用于演示：超时如何变成 `error`/`final`「调用失败…」，而不是前端一直转圈。

## 与 Ch4 关系

SSE 是**单次请求内**的流；进程被杀则中断。Durable run（Ch4）把 checkpoint 落库，才能跨请求 resume。


## 面试官追问（≥5）

**Q1：SSE 与 WebSocket 为何选 SSE？**  
A：服务端单向推步骤足够；实现简单，HTTP 友好。

**Q2：事件有哪些？**  
A：identity/budget/step_start/tool_*/final/paused/error/done（及 memory/supervisor）。

**Q3：中途断线？**  
A：SSE 丢；靠 durable run 恢复。

**Q4：如何在前端解析？**  
A：`frontend/src/api/agent.js` 读 event/data 行。

**Q5：force_timeout 演示意义？**  
A：证明错误路径可观测，不是只 Happy Path。
