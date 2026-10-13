# 课程大纲（重做 · 成都 Agent 应用/后端 20–30k）

质量条：**课记可追问 · Demo 真串得起来 · 工程非贴皮**。用户授权连续交付，章节间不卡确认。

| 章 | 主题 | 状态 | 课记 |
|----|------|------|------|
| Ch1 | 领域台账（隐患 + CAPA + ACL + 审计 + UI） | ✅ | [ch1-domain](./lessons/ch1-domain.md) |
| Ch2 | 手写 Agent 循环；工具只调本仓领域 API；可点 Agent UI | ✅ | [ch2-agent-loop](./lessons/ch2-agent-loop.md) |
| Ch3 | SSE 推送 steps/budget；超时可演练 | ✅ | [ch3-sse](./lessons/ch3-sse.md) |
| Ch4 | Durable run：checkpoint / pause / resume | ✅ | [ch4-durable-run](./lessons/ch4-durable-run.md) |
| Ch5 | Span Trace + Replay + 写工具 HITL | ✅ | [ch5-trace-hitl](./lessons/ch5-trace-hitl.md) |
| Ch6 | Mock 确定性 Eval 门禁 + Compose/Postgres | ⏳ | — |
| Ch7 | 面试追问稿 + 简历项目段 | ⏳ | — |

## 硬约束

- 工具不得旁路领域层：写台账必须走与 UI 相同的服务/状态机/审计
- 默认可 `LLM_PROVIDER=mock` 跑通 Demo；真 LLM 可选
- 每章：代码 + 中文课记 + pytest（适用时）+ push main
