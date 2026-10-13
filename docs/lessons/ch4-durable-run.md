# Ch4 课记：Durable Run（checkpoint / pause / resume）

## 问题

SSE 流挂在一次 HTTP 上：客户端断开或进程重启，中间状态就没了。  
生产 Agent 需要：**跑到一半能停、状态可持久化、之后从同一点续跑**。

## 设计

表 `agent_runs`：

| 字段 | 含义 |
|------|------|
| status | pending / running / paused / awaiting_approval / completed / failed |
| checkpoint_json | message、history、tool_results、steps、budget_used |
| steps_json | 已发生步骤副本（便于列表展示） |

`pause_after_steps=N`：完成 N 个循环步后写入 `paused` 并返回。  
`POST /api/runs/{id}/resume`：把 checkpoint 喂回 `stream_agent(resume_state=…)`。

## Demo

Runtime 页：消息「有哪些未闭环隐患？」，pause_after_steps=1 → 启动 → 状态 paused → Resume → completed。

## 面试要点

- checkpoint 存的是**决策状态**（工具结果），不是聊天 UI 缓存  
- resume **不重放**已成功的工具副作用（除非你故意设计 idempotent replay）——本实现从 next_index 继续 LLM 决策  
- 与 HITL（Ch5）共用 status：`awaiting_approval` 时禁止盲目 resume
