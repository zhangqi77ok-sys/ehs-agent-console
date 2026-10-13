# Ch2 课记：手写 Agent 循环（工具不旁路领域）

面试官常问：「你的 Agent 和 CRUD API 是什么关系？LLM 能不能直接改库？」

## 1. 架构一句话

```
用户 → Agent Loop（decide/act）→ Tool Registry → domain repo（CAPA/ACL/审计）→ DB
                                    ↑ 禁止旁路
```

手写循环，不绑 LangChain：预算步数内反复 `LLM.complete → tool_call | final`。  
工具实现全部落在 `app/tools/domain_tools.py`，内部只调 `app.db.repo`——与 Domain UI 同一条状态机与审计。

## 2. 为什么必须「工具 = 领域门面」

若 Agent 自己 `UPDATE tickets SET status=…`：

- CAPA 非法迁移不再拦截
- viewer 可能被 prompt 注入绕过
- 审计对不上「谁通过哪条路径改的」

面试答法：**Agent 是操作员，领域服务是法务与门禁；写台账只允许走同一道门。**

## 3. Mock LLM 做什么

`LLM_PROVIDER=mock`（默认）：关键词路由——「未闭环」→ `list_open_hazards`，HZ+开单 → `create_corrective_ticket`，TK+推进 → `advance_corrective_ticket`。  
工具结果回来后再生成 final 中文。  
真网关：`LLM_PROVIDER=openai` + `OPENAI_API_KEY` / `OPENAI_BASE_URL`。

## 4. Demo 路径

1. 顶栏切 **Agent** 页签  
2. 「有哪些未闭环隐患？」→ steps 出现 tool_call / tool_result / final  
3. 「给 HZ-2026-001 开整改单，措施：更换过期灭火器」→ 回 Domain 台账可见新单，审计有 `ticket.create`  
4. 角色改 **viewer** 再开单 → 回复失败，审计 `ticket.denied`

## 5. 追问储备

| 问 | 答要点 |
|----|--------|
| 为何不用 Agent 框架？ | 教学/面试要讲清循环与预算；框架可后加，边界在工具层 |
| 多步工具怎么控？ | `max_agent_steps`；超限 final 说明预算耗尽 |
| 租户怎么进工具？ | Identity 头 → ToolContext，repo 强制 `tenant_id` 过滤 |

下一章 Ch3：同一循环用 **SSE** 推送 steps/budget，前端可边跑边看。


## 面试官追问（≥5）

**Q1：一轮循环里 decide 失败怎么办？**  
A：捕获 `LLMCallError`，yield error/final，status failed。`loop.py`。

**Q2：工具参数校验在哪？**  
A：`run_tool` TypeError→错误返回；领域层再校验业务。

**Q3：history 如何影响 mock？**  
A：mock 主要看最新 tool_results 与 user message；真 LLM 带 history。

**Q4：为何工具结果要回灌？**  
A：observe 需要；否则无法生成基于台账的 final。

**Q5：最大步数如何配置？**  
A：`settings.max_agent_steps`。
