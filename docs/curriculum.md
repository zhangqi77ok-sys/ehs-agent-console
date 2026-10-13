# 课程大纲（重做 · 对齐成都 Agent 应用/后端 20–30k JD）

质量条：**课记可追问 · Demo 真串得起来 · 工程非贴皮**。连续交付，不卡确认。

对照 JD 高频（曙光/鼎桥/超精密光学/企微 Harness 类）：Runtime · Memory · RAG · 多 Agent · HITL · Eval · 可观测 · 多租户权限 · 工具沙箱。

| 章 | 主题 | 状态 | 课记 |
|----|------|------|------|
| Ch1 | 领域台账（隐患 + CAPA + ACL + 审计 + UI） | ✅ | [ch1-domain](./lessons/ch1-domain.md) |
| Ch2 | 手写 Agent 循环；工具只调领域 API；Agent UI | ✅ | [ch2-agent-loop](./lessons/ch2-agent-loop.md) |
| Ch3 | SSE steps/budget；超时演练 | ✅ | [ch3-sse](./lessons/ch3-sse.md) |
| Ch4 | Durable run checkpoint/pause/resume | ✅ | [ch4-durable-run](./lessons/ch4-durable-run.md) |
| Ch5 | Span Trace + Replay + 写工具 HITL | ✅ | [ch5-trace-hitl](./lessons/ch5-trace-hitl.md) |
| Ch6 | Mock Eval 门禁 + Compose/Postgres | ✅ | [ch6-eval-compose](./lessons/ch6-eval-compose.md) |
| Ch7 | 面试追问 + 简历段 | ✅ | [ch7-interview](./lessons/ch7-interview.md) |
| Ch8 | JWT/API Key 鉴权 + request_id 访问日志（多租户可讲） | ✅ | [ch8-auth-obs](./lessons/ch8-auth-obs.md) |
| Ch9 | 法规/制度向量 RAG 工具（切块+检索，可 mock embedding） | ✅ | [ch9-rag](./lessons/ch9-rag.md) |
| Ch10 | 会话记忆分层 + 上下文压缩（长对话不炸预算） | ✅ | [ch10-memory](./lessons/ch10-memory.md) |
| Ch11 | Supervisor 多 Agent（排查员/开单员）真派发 | ✅ | [ch11-multi-agent](./lessons/ch11-multi-agent.md) |
| Ch12 | 就业包：JD 对照表 + Demo 脚本 + 作品集 README | ⏳ | — |

## 硬约束

- 工具不得旁路领域层（状态机 + 审计）
- `LLM_PROVIDER=mock` 必须能演示全链路；真 LLM 可选
- 每章：代码 + 中文课记 + pytest + push main
