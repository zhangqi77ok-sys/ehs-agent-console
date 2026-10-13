# 10 分钟面试官 Demo 脚本（可扩到 15 分钟口述）

前置：`LLM_PROVIDER=mock`，前后端已起；浏览器 Domain / Agent / Runtime。

| 分 | 动作 | 你要说的一句话 |
|----|------|----------------|
| 0:00 | 打开 README/大纲 | 「领域优先，再挂 Runtime；工具不旁路 CAPA/ACL/审计。」 |
| 1:00 | Domain：viewer 尝试开单 | 「只读角色 403 且审计 denied。」 |
| 2:00 | Domain：工程师推进关单 | 「关闭强制 evidence_note，否则状态机拒绝。」 |
| 3:30 | Agent：查未闭环 | 「手写循环 observe→decide→act，SSE 看 steps。」 |
| 5:00 | Agent：查制度（RAG） | 「制度切块+本地 embedding，工具返回 source/score。」 |
| 6:00 | Agent：多 Agent 先查再开单 | 「Supervisor→Investigator→Clerk，双时间线+工具白名单。」 |
| 7:30 | Runtime：HITL 写工具 | 「写工具人工闸门，批准后才进领域。」 |
| 8:30 | pause/resume 或 Trace | 「checkpoint 落库；span 可 replay。」 |
| 9:30 | 提 Eval + JWT | 「mock eval 进 pytest；JWT/API Key 与演示头并存。」 |
| 10:00 | 收口 | 「差距：真 LLM 评测、OIDC、OTel、图编排——我清楚边界。」 |

失败演练（穿插 30s）：勾「强制超时」→ 错误可观测；换 `other-plant` → 看不到 demo 台账。
