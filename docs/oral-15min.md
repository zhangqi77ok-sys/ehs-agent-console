# 15 分钟口述稿（项目深挖）

## 0–2′ 定位（STAR 开场）

我做的是 **EHS 隐患整改 Agent 控制台**：先把隐患台账、整改单 CAPA、租户角色和只追加审计做成可测领域层，再在上面挂 **手写 Agent Runtime**。工具只能调领域 API，不能直接写库。目标是对齐成都 Agent 应用/后端岗对 Runtime、HITL、Eval、RAG、多 Agent、多租户的要求。

## 2–6′ 领域边界（必问）

状态机：待执行→执行中→待验收→已关闭/驳回；**close 必须 evidence_note**。viewer 写操作 403 并记 `ticket.denied`。跨租户按 `tenant_id` 过滤。代码：`domain/capa.py`、`auth/tenant.py`、`db/repo.py`。

## 6–11′ Runtime 能力

- 循环：`agent/loop.py`，预算步数，mock/openai 双通道  
- SSE：steps/budget 推送  
- Durable：`agent_runs.checkpoint_json` pause/resume  
- HITL：写工具集合闸门 → approvals  
- Trace：steps→spans，replay 不重放副作用  
- Eval：`eval/cases.json` + mock 进 pytest  

## 11–14′ 就业补强章

- Ch8 JWT/API Key + request_id JSON 日志  
- Ch9 法规 RAG（切块+hash embed+score）  
- Ch10 session 记忆压缩  
- Ch11 Supervisor 双角色时间线 + allowlist  

## 14–15′ 主动暴露差距

没有 OIDC/JWKS、没有生产向量库与 OTel、Multi-Agent 是顺序路由不是图编排、真 LLM 评测未进 CI。我能讲清「已做到 / 刻意没做 / 上线怎么补」。
