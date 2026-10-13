# 面试追问稿（成都 · Agent 应用 / 后端 · 20–30k）

面向：把本仓库当项目经历时，面试官可能追问的问题与标准答法。  
原则：**先领域边界，再 Agent 能力；能量化就量化；能指到代码路径就指。**

---

## A. 项目定位（开场 60 秒）

> 我做了一套 EHS 隐患整改控制台：先把隐患台账、整改单状态机、租户角色和审计做成可点可测的领域层，再在上面挂手写 Agent 循环。工具只调同一套领域 API，不能旁路。支持 SSE 观察步骤、durable run 暂停续跑、写工具人工审批、mock 确定性评测，以及 Compose/Postgres 生产形状。默认 mock LLM 可离线 Demo，也可接 OpenAI 兼容网关。

---

## B. 领域 / CAPA / 审计（高频）

**Q1：为什么先做领域再做 Agent？**  
A：业务怕的是假闭环、无证据关单、跨厂串数据。Agent 只是操作员；领域不可靠时 LLM 只会加速脏数据。所以 Ch1 DoD（状态机+ACL+审计+UI）未达成前不上 Agent。

**Q2：整改单状态机怎么设计？关闭为何强制 evidence？**  
A：待执行→执行中→待验收→已关闭/驳回。close 必须非空 `evidence_note`，拒绝也写 `ticket.denied` 审计。EHS 场景口头完成不够，要可复核痕迹。

**Q3：viewer 和跨租户怎么防？**  
A：头 `X-Tenant-Id` / `X-Role`；viewer 写 403 且审计 denied；跨租户按 tenant 过滤，别厂 ticket 返回 404 不泄露存在性。

**Q4：审计和操作日志区别？**  
A：审计面向合规追责：谁/何时/改什么/成功否，只追加；不是 debug 日志。

---

## C. Agent 循环 / 工具边界

**Q5：为什么手写循环不用 LangChain？**  
A：面试要讲清 observe→decide→act、预算、checkpoint；框架可后加。边界放在工具层：一律 `domain_tools → repo`。

**Q6：LLM 能不能直接 UPDATE 数据库？**  
A：不能。只允许工具调用；写工具再经 CAPA/ACL。HITL 对写工具二次闸门。

**Q7：mock 和真 LLM 怎么切换？**  
A：`LLM_PROVIDER=mock|openai`。mock 关键词路由保证 CI/Demo 稳定；openai 走兼容 `/chat/completions`，带超时重试。

---

## D. SSE / Durable / HITL / Trace

**Q8：SSE 解决什么？和 durable run 什么关系？**  
A：SSE 是单次请求内推送 steps/budget，方便演示观察性。进程杀了就没了；durable run 把 checkpoint JSON 落库，才能 pause/resume。

**Q9：resume 会不会重复执行已成功的工具？**  
A：本实现从 `budget_used/next_index` 继续决策，已有 `tool_results` 留给 LLM 生成 final，不主动重放副作用。幂等若要做需工具层另设计。

**Q10：为什么只对写工具做 HITL？**  
A：读台账风险低；开单/关单不可逆且进审计。人守副作用边界，不是每个 token。

**Q11：Trace/Replay 怎么用？**  
A：steps 派生 spans；`failure_mode` 分类超时/拒写/预算等。Replay 只读轨迹，不重新调 LLM，用于排障与评测对照。

---

## E. Eval / 工程化

**Q12：评测怎么保证 CI 不抖？**  
A：固定 cases + mock：断言工具名与回复关键词。`pytest` 始终跑 eval；真 LLM 评测单独跑、不挡合并。

**Q13：本地 SQLite 和生产 Postgres？**  
A：pytest/开发默认 SQLite；Compose 起 Postgres + alembic on start + nginx 反代。同一套 ORM/迁移。

---

## F. 压力 / 反问

**可能被怼：**「这不就是套壳 ChatGPT？」  
回应：领域状态机与审计是硬边界；Agent 轨迹可暂停、可审批、可回放、可评测——这是应用后端能力，不是聊天皮肤。

**你可反问：**贵司 Agent 写操作的审批与审计现在落在哪一层？有没有 trajectory eval？

---

## G. Auth / RAG / Memory / Multi-Agent（Ch8–Ch11）

**Q14：多租户鉴权怎么讲？**  
A：JWT / API Key / 演示头同一 `get_identity`；隔离在查询层。见 `docs/lessons/ch8-auth-obs.md`。

**Q15：法规 RAG 没接向量库算不算？**  
A：有切块、本地 embedding、score、工具进 eval；生产可换 pgvector。路径 `app/rag/`。

**Q16：长对话如何不炸？**  
A：session 落库 + char 预算压缩。`app/memory/compress.py`。

**Q17：多 Agent 如何证明真派发？**  
A：工具 allowlist + UI 双时间线 + handoff 测例。`app/agent/supervisor.py`。

**Q18：就业材料在哪？**  
A：`docs/jd-gap-matrix.md`、`oral-15min.md`、`mock-interview.md`、`failure-mode-drill.md`。

---

## H. 把握与风险（诚实）

仓库不能保证 offer。冲刺 20–30k 时：本仓把高频技术追问落到代码与 Demo；剩余风险是**口语流畅度、真 LLM 临场、公司业务匹配、学历/年限门槛**。用 `mock-interview.md` 闭卷练到不看稿。


## Ch13–17 追问速记

- **Tracing vs Logging**：access log = 请求级；spans = Agent 步级；`failure_mode` 分类见 `runs/trace.py`。
- **pgvector**：Compose 用 pgvector 镜像；sqlite 仍内存索引；切 `DATABASE_URL`。
- **MCP**：`/api/mcp/tools` + `/call` 薄层，不是完整 SSE 协议。
- **多维 Eval**：tool_correct / reply_quality / latency / policy_deny。
- **Practice**：三档自评；**不能保证 offer**。
