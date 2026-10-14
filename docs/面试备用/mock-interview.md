# 模拟面试 30 问（答案点到本仓路径）

> ⚠️ **先别看这份——跟完 [docs/跟我学](../跟我学/README.md) 再来。**


覆盖：Runtime / HITL / Eval / RAG / Memory / Multi-agent / ACL。练习时闭卷口述，再核对。

---

## A. 领域与 ACL（1–5）

**1. 为什么领域优先于 Agent？**  
答：业务怕假闭环。Ch1 DoD 未达成不上 Agent。规格：`docs/superpowers/specs/2026-10-13-ehs-domain-ch1-design.md`。

**2. 关闭整改单为何强制证据？**  
答：`domain/capa.py` close 校验非空 `evidence_note`；拒绝写审计。

**3. viewer 写会被怎样处理？**  
答：403 + `ticket.denied`（`auth/deps.py` `deny_if_readonly` / tools 内 `_deny_write`）。

**4. 跨租户如何防枚举？**  
答：查询带 `tenant_id`；别厂资源 404（`db/repo.py`）。

**5. 审计和 access log 区别？**  
答：审计=`audit_events` 合规追责；access log=`middleware/observability.py` 运维请求级。

## B. Agent Runtime（6–12）

**6. 手写循环步骤？**  
答：observe→decide→act，`agent/loop.py` `stream_agent`。

**7. 为何不直接上 LangChain？**  
答：要讲清预算/checkpoint/HITL；框架可后加，边界在工具层。

**8. 工具如何保证不旁路？**  
答：`domain_tools` 只调 `repo.*`，不拼 SQL 更新状态。

**9. mock 与真 LLM？**  
答：`LLM_PROVIDER`；`llm.py` mock 关键词路由；openai 兼容 chat completions。

**10. SSE 解决什么？**  
答：单次请求内推 steps/budget；进程杀了就没——故有 durable。

**11. resume 会否重复副作用？**  
答：从 `budget_used` 续决策，已有 tool_results 不主动重放；真幂等需工具层设计。

**12. 预算耗尽怎么办？**  
答：final 提示达最大步数；可 pause/resume 或缩小问题。

## C. HITL / Trace（13–16）

**13. 为何只拦写工具？**  
答：读风险低；开单/关单不可逆。`hitl_write_tool_set`。

**14. 审批落在哪？**  
答：`agent_approvals` + Runtime API；状态 `awaiting_approval`。

**15. Trace span 从哪来？**  
答：steps 派生，`runs/trace.py`；replay 只读。

**16. failure_mode 有哪些？**  
答：超时、拒写、预算、HITL deny 等——见 `failure-mode-drill.md`。

## D. Eval / 工程化（17–19）

**17. Eval 如何不抖？**  
答：固定 `eval/cases.json` + mock；`test_eval_deterministic.py` 进 pytest。

**18. SQLite 与 Postgres？**  
答：开发/测 SQLite；Compose Postgres + alembic。同一 ORM。

**19. CI 里跑什么？**  
答：pytest（含 eval）；真 LLM 评测不挡合并。

## E. Auth / Obs（20–22）

**20. 三种身份方式优先级？**  
答：JWT → API Key → 头。`auth/deps.py`。

**21. JWT claims 放什么？**  
答：tenant_id/role/actor + exp。`jwt_tokens.py`。

**22. request_id 用途？**  
答：串联 HTTP 与排障；响应头回写。

## F. RAG / Memory / Multi-agent（23–28）

**23. RAG 流水线？**  
答：md 切块 → hash embed → 余弦 top_k → `search_regulations`。

**24. 无向量库如何面试自洽？**  
答：本地可复现；生产可换 FAISS/pgvector，接口已是 store.search。

**25. 记忆压缩触发条件？**  
答：`estimate_chars > memory_max_chars`；摘要旧轮次。`memory/compress.py`。

**26. 如何证明压缩后仍可用？**  
答：`test_memory.py::test_long_history_agent_still_completes`。

**27. Investigator 与 Clerk 权限差？**  
答：READ_TOOLS vs READ+WRITE；allowlist 强制。`supervisor.py`。

**28. 双时间线怎么演示？**  
答：「先查…再开单」handoff；UI 两列 Timeline。Agent 页多 Agent。

## G. 软性 / 反杀（29–30）

**29. 别人说你是套壳 ChatGPT？**  
答：领域状态机+审计硬边界；可暂停、可审批、可回放、可评测、可多租户——是应用后端。

**30. 你项目离 20–30k 岗还差什么？**  
答：口语与临场；真 LLM 稳定性；OIDC/OTel/图编排；业务域匹配。仓库不能保证 offer，但能把问题答到码上。
