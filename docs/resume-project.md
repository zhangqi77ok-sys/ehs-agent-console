# 简历项目段（成都 Agent 应用/后端 · 20–30k 口径）

> 完整就业包（演示稿、口头题、差距清单）见 **[就业过关 · 最终版](./就业过关-最终版.md)**。  
> 学操作先走 [最终版 · 保姆级全书](./最终版-保姆级全书.md)。

> 无仓库能保证 offer；以下按可追问、可演示、可指代码来写。

## 版本 A（推荐 · STAR 条）

**EHS 隐患整改 Agent 控制台**｜个人项目｜Python / FastAPI / SQLAlchemy / React  

- **背景：** 工业安全场景要整改可审计、可多租户，并要能演示真正的 Agent 运行时（不是聊天套壳）。  
- **做法：** 先做隐患台账 + 整改状态机（关单强制验收证据）+ 租户/角色权限 + 只追加审计；再手写 Agent 循环，工具统一走领域层；SSE 推步骤与预算；任务可暂停续跑；写操作人工审批；步骤可 Trace/回放；mock 评测进测试；Compose/Postgres；并补上 JWT、制度检索、会话压缩、双角色多 Agent。  
- **结果：** 前后端可点通闭环；技术点可对照 Runtime / 审批 / 评测 / 检索 / 多租户当面演示并指到代码路径。  

技术关键词：Agent 运行时 · 工具白名单 · 人工审批 · SSE · 可暂停任务 · 评测门禁 · RAG · 会话压缩 · 多 Agent · JWT · 多租户权限

## 版本 B（短）

EHS Agent 控制台：整改关单要证据 + 权限/审计 + 手写运行时（流式/暂停/审批/回放/评测）+ JWT 可观测 + 制度检索 + 会话压缩 + 双角色协作；mock 全链路可测。

## 版本 C（English）

**EHS Corrective-Action Agent Console** — Domain-first CAPA (evidence-gated close, tenant ACL, append-only audit); handwritten agent runtime with tool allowlists, SSE, durable pause/resume, HITL on writes, span replay, deterministic mock eval; JWT/API-key auth with request_id logs; regulations RAG; session memory compression; supervisor multi-agent (investigator/clerk timelines).

## 投递时一句自信版（可直接用）

独立完成 EHS 隐患闭环 Agent 控制台（FastAPI + React）：手写运行时（流式、断点续跑、写操作审批、步骤回放）、领域状态机与审计、制度检索、会话压缩、双角色多 Agent、JWT、评测门禁与 Compose/Postgres。面向成都 Agent 应用/后端岗，可当面演示并指代码。
