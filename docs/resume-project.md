# 简历项目段（可直接粘贴）

## 版本 A（偏后端 / Agent 应用 · 推荐）

**EHS 隐患整改 Agent 控制台**（个人项目）  
Python / FastAPI / SQLAlchemy / React · 手写 Agent 循环  

- 领域优先：隐患台账 + 整改单 CAPA 状态机（关闭强制验收证据）+ 租户/角色 ACL + 只追加审计；前后端可点通完整闭环  
- Agent 工具统一调用领域服务，禁止旁路；支持 mock/OpenAI 兼容双通道；SSE 推送 steps/budget  
- Durable run：checkpoint 落库，支持 pause/resume；写工具 HITL 人工审批；Span Trace / Replay 排障  
- 确定性 mock Eval 进 pytest 门禁；Docker Compose（Postgres + API + Nginx）生产形状  

技术关键词：Agent Runtime、Tool Gateway、HITL、SSE、Checkpoint、Eval、多租户

## 版本 B（更短 · 一行半）

EHS Agent 控制台：领域 CAPA/ACL/审计 + 手写 Agent（工具不旁路）+ SSE/Durable Run/HITL/Trace + mock Eval 与 Compose/Postgres。

## 版本 C（英文）

**EHS Corrective-Action Agent Console** — Domain-first CAPA ledger (evidence-gated close, tenant ACL, append-only audit), handwritten agent loop with tools that only call the domain layer, SSE step streaming, durable pause/resume, HITL on write tools, span trace/replay, deterministic mock eval in CI, and Docker Compose (Postgres).
