# JD 关键词 → 本仓路径 / Demo 步骤

对照成都 Agent 应用/后端（约 20–30k）高频 JD：曙光类平台、鼎桥、超精密光学、企微 Harness 等口径。

| JD 关键词 | 本仓证据 | Demo / 面试指认 |
|-----------|----------|-----------------|
| Agent Runtime / 手写循环 | `backend/app/agent/loop.py` | Agent 页发「查灭火器」，看 steps |
| Tool Gateway / 工具不旁路 | `tools/domain_tools.py` → `db/repo.py` | 开单后 Domain 台账+审计同步变 |
| HITL 人工审批 | `runs/approvals.py` · Runtime 页 | 写工具 awaiting_approval → 批准 |
| SSE / 可观测流 | `api/agent.py` `/chat/stream` | 勾选 SSE，逐步刷 steps/budget |
| Durable / Checkpoint | `runs/service.py` · `agent_runs` | pause_after_steps → resume |
| Trace / Replay | `runs/trace.py` · Runtime | 看 spans / replay 只读 |
| Eval 门禁 | `eval/cases.json` · `scripts/run_eval.py` | `pytest` 含确定性 mock eval |
| 多维 Eval | Ch16 dimensions + `docs/eval-dashboard.md` | tool/reply/latency/policy_deny 表 |
| 多租户 / ACL | `auth/tenant.py` · Ch1 测例 | viewer 写 403；换租户 404 |
| JWT / API Key | `auth/jwt_tokens.py` · `/auth/token` | Bearer 调 `/api/hazards` |
| request_id / 访问日志 | `middleware/observability.py` | 响应头 `X-Request-Id` |
| Metrics / 摘要 | `/api/obs/summary` · `/metrics` | Runtime 顶栏 deny rate / HITL |
| RAG / 知识库 | `rag/*` · `search_regulations` | 「查制度：灭火器过期」 |
| pgvector 路径 | `rag/pg_store.py` · Compose pgvector 镜像 | 切 `DATABASE_URL` 见 Ch14 课记 |
| Memory / 上下文压缩 | `memory/compress.py` | 长 session 后 `memory.compressed` |
| Multi-Agent | `agent/supervisor.py` | 先查再开单 → 双时间线 |
| MCP（薄层） | `/api/mcp/tools` · `/api/mcp/call` | 列表 schema + invoke；非完整 SSE |
| Compose / Postgres | `docker-compose.yml` | `docker compose up --build` |
| CAPA / 领域状态机 | `domain/capa.py` | 无 evidence 关单失败+审计 |
| 面试练习 | Practice Tab · `practice-rubric.md` | 完整/能答/不会 localStorage |

## 诚实未覆盖（面试主动说）

- 真 LLM 评测集与线上灰度；生产 ANN 调参 / 多租户语料隔离
- JWKS / OIDC SSO、细粒度 RBAC、单据级权限
- OpenTelemetry OTLP 全链路导出；限流熔断平台化
- 完整 MCP SSE/stdio 传输与 capability 协商（仅 schema+invoke 薄层）
- 并行 Multi-Agent 图编排（LangGraph 级）

## 残留风险（对「保证面试成功」）

仓库可以把技术追问空白压到很低，**不能**保证 offer。剩余变量：口语表达、项目与 JD 匹配度、对手盘、真 LLM 临场、系统面/行为面。Practice 分只是自评工具。
