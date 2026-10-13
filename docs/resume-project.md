# 简历项目段（成都 Agent 应用/后端 · 20–30k 口径）

> 无仓库能保证 offer；以下按可追问、可演示、可指代码来写。

## 版本 A（推荐 · STAR 条）

**EHS 隐患整改 Agent 控制台**｜个人项目｜Python / FastAPI / SQLAlchemy / React  

- **S/T**：面向工业安全场景，要求整改可审计、可多租户，并具备可演示的 Agent Runtime（非聊天套壳）。  
- **A1 领域**：实现隐患台账 + CAPA 状态机（关闭强制验收证据）+ 租户/角色 ACL + 只追加审计；前后端可点通闭环（`domain/capa.py`）。  
- **A2 Runtime**：手写 Agent 循环，工具统一经领域层；SSE 推送 steps/budget；checkpoint 落库支持 pause/resume；写工具 HITL；Span Trace/Replay。  
- **A3 质量**：`LLM_PROVIDER=mock` 确定性 Eval 进入 pytest；Docker Compose（Postgres）生产形状。  
- **A4 就业深度**：JWT/API Key 混合鉴权 + request_id JSON 访问日志；法规 RAG（切块+本地 embedding+score）；会话记忆压缩；Supervisor 多 Agent（Investigator/Clerk 双时间线 + 工具白名单）。  
- **R**：独立完成 Ch1–Ch12 可演示作品集；配套 JD 对照表、15 分钟口述稿、30 问模拟面试与失败演练清单，面试可指到具体路径。

技术关键词：Agent Runtime · Tool Allowlist · HITL · SSE · Checkpoint · Eval · RAG · Memory · Multi-Agent · JWT · 多租户 ACL

## 版本 B（短）

EHS Agent 控制台：领域 CAPA/ACL/审计 + 手写 Runtime（SSE/Durable/HITL/Trace/Eval）+ JWT 可观测 + 法规 RAG + 记忆压缩 + Supervisor 双角色时间线；mock 全链路可 CI。

## 版本 C（English）

**EHS Corrective-Action Agent Console** — Domain-first CAPA (evidence-gated close, tenant ACL, append-only audit); handwritten agent runtime with tool allowlists, SSE, durable pause/resume, HITL on writes, span replay, deterministic mock eval; JWT/API-key auth with request_id logs; regulations RAG; session memory compression; supervisor multi-agent (investigator/clerk timelines).
