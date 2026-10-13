# 失败模式演练清单（面试可现场做）

| # | 场景 | 操作 | 期望 | 代码/页 |
|---|------|------|------|---------|
| 1 | LLM/工具超时 | Agent 勾「强制超时」 | 明确失败文案；status failed；可观测 | `loop.py` / `llm.py` |
| 2 | HITL 拒绝 | Runtime 写工具 → 拒绝 | 不落开单；approval denied；台账不变 | `approvals.py` |
| 3 | HITL 通过 | 同上 → 批准 | 领域开单成功 + 审计 ok | Runtime 页 |
| 4 | 跨租户 | 头改 `other-plant` 读 demo 单号 | 404/空列表，不泄露 | `repo` + ACL 测例 |
| 5 | viewer 写 | 角色 viewer 开单 | 403 + `ticket.denied` 审计 | Domain / tools |
| 6 | 无证据关单 | close 空 evidence | 状态机拒绝 | `capa.py` |
| 7 | 预算耗尽 | 降低 max steps / 复杂任务 | final 提示达最大步数 | `loop.py` |
| 8 | 压缩后仍可用 | 长 session 再查台账 | `memory.compressed=true` 且工具成功 | `test_memory.py` |
| 9 | Investigator 拒写 | allowlist 外写工具 | `denied: true` | `registry.run_tool` |
| 10 | 坏 JWT / 坏 Key | Bearer 乱码 / 错 Key | 401 | `test_auth_obs.py` |

面试话术：先演示 **正常闭环**，再主动点 1/2/4，证明你做的是可控系统不是 Demo 幸福路径。
