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
| 多租户 / ACL | `auth/tenant.py` · Ch1 测例 | viewer 写 403；换租户 404 |
| JWT / API Key | `auth/jwt_tokens.py` · `/auth/token` | Bearer 调 `/api/hazards` |
| request_id / 访问日志 | `middleware/observability.py` | 响应头 `X-Request-Id` |
| RAG / 知识库 | `rag/*` · `search_regulations` | 「查制度：灭火器过期」 |
| Memory / 上下文压缩 | `memory/compress.py` | 长 session 后 `memory.compressed` |
| Multi-Agent | `agent/supervisor.py` | 先查再开单 → 双时间线 |
| Compose / Postgres | `docker-compose.yml` | `docker compose up --build` |
| CAPA / 领域状态机 | `domain/capa.py` | 无 evidence 关单失败+审计 |

## 诚实未覆盖（面试主动说）

- 真 LLM 评测集与线上灰度；向量库生产形态（pgvector）
- JWKS / OIDC SSO、细粒度 RBAC、单据级权限
- OpenTelemetry 全链路；限流熔断平台化
- 并行 Multi-Agent 图编排（LangGraph 级）
