# Ch11 课记：Supervisor 多 Agent

## 面试怎么讲

1. **为什么拆**：排查（读台账/法规）与开单（写 CAPA）风险不同；拆成 Investigator / Clerk，Supervisor 只做路由，权限面更清晰。
2. **真派发不是贴皮**：子 Agent 有独立 `agent` 标签与 **工具 allowlist**；Investigator 即使被诱导也无法执行写工具。
3. **和 HITL 关系**：Clerk 仍可走写工具 HITL；Supervisor 不替代人工审批。
4. **诚实差距**：当前是关键词路由 + 顺序子循环，不是并行图编排 / 共享黑板；未接 LangGraph，但边界模型可迁移。

## 路径

- `app/agent/supervisor.py`
- `POST /api/agent/chat` · `multi_agent=true`
- UI：Agent 页「多 Agent」开关，Steps 显示 `investigator|clerk|supervisor`
