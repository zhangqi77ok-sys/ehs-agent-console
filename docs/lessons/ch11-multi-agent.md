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


## 面试官追问（≥5）

**Q1：多 Agent 是不是多个 LLM 角色扮演？**  
A：不只是 prompt。本仓 Supervisor 路由 + **工具 allowlist**：Investigator 只有 `READ_TOOLS`，Clerk 才有写工具（`supervisor.py` / `registry.py`）。

**Q2：如何证明不是贴皮？**  
A：UI 双时间线（Investigator / Clerk 两列）；handoff 场景 steps 里同时有两角色；`run_tool(..., allowed=)` 拒写。

**Q3：何时 handoff？**  
A：`needs_investigator_handoff`：写意图且需要先查（含「先查…再开单」）。先只读排查再 Clerk 开单。

**Q4：和 HITL 谁先谁后？**  
A：Supervisor 选角色 → Clerk 若调写工具 → HITL（Ch5）仍可拦。路由不替代人工审批。

**Q5：和生产 LangGraph 差距？**  
A：诚实：关键词路由 + 顺序子循环，非并行图/共享黑板。但「权限按角色切工具」模型可迁到图编排。
