# 工业级课纲（Ind）· 冲成都 Agent 应用/后端 20–30K

> **诚实口径**：v2 Ch1–9 + Eng-01～04 = 能讲清楚的作品集底座。  
> **本课纲**对齐猎聘/鼎桥/腾讯 Harness 类 JD 高频词：Runtime 断点续跑、Trace/回放、HITL、确定性 Eval、Compose/Postgres、工具审计。  
> 「大概率过面」仍取决于你的口述 + Demo + 对 JD 的对齐；教程负责把**可追问的工程深度**做实，不保证 offer。

## 对照缺口

| JD 高频 | 当前仓库 | Ind 目标 |
|---------|----------|----------|
| Agent Runtime / 长任务状态恢复 | 单次请求内存循环 | **Ind-01** run checkpoint / resume |
| Trace / Replay / 失败归因 | 仅 request_id 访问日志 | **Ind-02** LLM/tool span + 回放 API |
| Human-on-the-loop | 无 | **Ind-03** 写工具审批闸 |
| Eval harness / CI 回归 | eval 需真 LLM；CI skip | **Ind-04** mock 确定性评测进 CI |
| Docker / Postgres / 可交付形态 | 默认 SQLite 本机 | **Ind-05** Compose + Postgres |
| 工具沙箱 / 审计 / 最小授权 | 角色白名单雏形 | **Ind-06** 工具策略 + 审计表 |
| Memory / 上下文压缩 | 仅 session 原文 | **Ind-07** 摘要压缩 + 分层记忆 |
| Multi-agent / 编排 | 单 Agent | **Ind-08** Supervisor 派生子任务（薄但真） |

## 进度

| 序号 | 主题 | 课记 | 状态 |
|------|------|------|------|
| Ind-01 | 长任务 Run：checkpoint / 暂停 / 续跑 | [ind-01-durable-run](./lessons/ind-01-durable-run.md) | ✅ |
| Ind-02 | Span Trace + 回放 | [ind-02-trace-replay](./lessons/ind-02-trace-replay.md) | ✅ |
| Ind-03 | 写操作 HITL 审批 | [ind-03-hitl](./lessons/ind-03-hitl.md) | ✅ |
| Ind-04 | CI 确定性 Eval 门禁 | — | 待做 |
| Ind-05 | Docker Compose + Postgres | — | 待做 |
| Ind-06 | 工具策略与审计日志 | — | 待做 |
| Ind-07 | 上下文压缩与记忆分层 | — | 待做 |
| Ind-08 | 多 Agent 编排（Supervisor） | — | 待做 |

每完成一章：代码 + 中文课记 + pytest + push main。测不过不宣称完成。
