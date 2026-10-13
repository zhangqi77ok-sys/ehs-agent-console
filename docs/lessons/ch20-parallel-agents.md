# Ch20 课记：并行 Multi-Agent fan-out

## 交付

- `needs_parallel_fanout`：同时/并行/一边… 或「查…并起草」且非「先…再」
- `asyncio.gather` 并行跑 Investigator + Clerk（**各自独立 DB Session**）
- 汇合 note `parallel_join`；回复拼 `【Investigator】` / `【Clerk】`
- UI：`parallel` 徽章 + 双列时间线标题标注并行

## 与 handoff 对比

| | Handoff（Ch11） | Parallel（Ch20） |
|--|-----------------|------------------|
| 触发 | 先查再开单 | 同时查+起草/开单 |
| 执行 | 顺序 | gather 并行 |
| Session | 共用 | 各开一个（防并发写冲突） |
| UI | 双时间线 | 双时间线 + parallel 徽章 |

## 面试官追问（≥5）

**Q1：为何并行要两个 Session？**  
A：SQLAlchemy Session 非并发安全；并行子 Agent 若共享会竞态。

**Q2：并行会不会重复开单？**  
A：可能。生产要用幂等键 / 单据锁；本仓 demo 假设用户意图明确。诚实说限制。

**Q3：和 LangGraph 并行边？**  
A：概念类似 fan-out/fan-in；本仓无图 DSL、无共享黑板，但是可迁移的边界模型。

**Q4：HITL 怎么办？**  
A：Clerk 分支仍可走 HITL；Investigator 只读默认关 HITL。

**Q5：如何证明真并行？**  
A：测例断言 `supervisor.parallel`、两侧 agent 标签、`parallel_join`；实现是 `asyncio.gather` 不是 for 循环顺序。

**Q6：什么时候不该并行？**  
A：写依赖读结果时（必须先查到 id 再开单）→ 用 handoff。
