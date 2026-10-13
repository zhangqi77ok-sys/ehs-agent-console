# EHS Agent Console · Ch1 领域重做设计

- 日期：2026-10-13
- 状态：待用户审阅规格（通过后清库重做，再写实现计划）
- 目标岗：成都 Agent 应用/后端约 20–30k
- 骨架：**domain-first**（领域够厚才允许上 Agent）
- 质量条：课记可追问 + Demo 真串得起来 + 工程非贴皮（all-of-above）

## 1. 问题与边界

上一版 v2/Eng/Ind 被判定偏流水账、Demo 假、Runtime/评测/多租户贴皮。`main` 将清空后按本规格从零重做。

**Ch1 只做领域台账系统**，明确 **不做**：

- Agent 循环 / LLM / SSE 聊天
- HITL / Trace / Eval / 多 Agent
- 向量 RAG

上述能力列入后续章节，**Ch1 DoD 未达成前不得开工**。

## 2. 成功标准（Ch1 DoD）

全部满足才算 Ch1 完成：

1. **隐患台账**：可列表/筛选（状态、级别、车间）；种子数据可演示真实 EHS 语境（消防/电气等）。
2. **整改单状态机**：`待执行 → 执行中 → 待验收 → 已关闭`；`待验收 → 执行中`（驳回）。非法迁移返回明确错误，不静默改状态。
3. **验收证据**：关闭（`close`）必须提供非空 `evidence_note`；否则 400，并写入审计为拒绝原因。
4. **角色隔离**：`viewer` 只读；`ehs_engineer` 可开单与推进；`admin` 同工程师并可见审计全量。跨 `tenant_id` 不可读写。
5. **写操作审计**：开单、推进、驳回、拒绝（含权限拒绝与证据不足）均落库：谁、租户、动作、目标 id、前后状态摘要、结果 ok/denied、时间。
6. **可点 UI**：领域页可完成「查隐患 → 开整改单 → 推进到待验收 → 填证据关闭 → 看审计」，无需聊天。
7. **课记**：中文一篇，按面试追问组织（为何这几态、为何关闭要证据、审计查什么），附本地复现步骤；禁止只贴命令清单。
8. **测试**：pytest 覆盖状态机合法/非法迁移、viewer 写拒绝、跨租户 403、关闭无证据失败、审计条数增长。

非目标：Postgres/Compose 可在 Ch1.5 或 Ch2 前补；Ch1 默认 SQLite 可验收。

## 3. 架构

单体仓库，两进程开发：

| 层 | 技术 | 职责 |
|----|------|------|
| API | FastAPI + SQLAlchemy + Alembic | 领域 REST、鉴权、审计 |
| UI | Vite + React | 仅领域台账面板 |
| DB | SQLite 默认（`DATABASE_URL`） | hazards / tickets / audit_events |

请求头身份（与后续 JWT 兼容的过渡形态）：`X-Tenant-Id`、`X-Role`。Ch1 不强制 JWT，但身份解析集中在一处，禁止各路由私自读 header。

## 4. 领域模型

### 4.1 Hazard（隐患）

- `id`（如 HZ-2026-001）、`title`、`description`、`plant`、`area`、`category`、`level`（一般/重大）
- `status`：待整改 / 整改中 / 待验收 / 已闭环 / 逾期（逾期可由 deadline 派生展示）
- `owner`、`deadline`、`discoverer`、`discovered_at`、`closed_at?`、`risk_note?`
- 归属：逻辑上属租户；Ch1 用请求租户过滤（单库多租户字段 `tenant_id`）

### 4.2 Ticket（整改单 / CAPA）

- `ticket_id`、`hazard_id`、`tenant_id`、`measures`、`owner`、`due_date`
- `status`：待执行 / 执行中 / 待验收 / 已关闭
- `evidence_note`：验收说明；关闭前必须非空

**迁移表（唯一真相）：**

| action | from | to | 额外规则 |
|--------|------|-----|----------|
| start | 待执行 | 执行中 | — |
| submit_verify | 执行中 | 待验收 | 可附 evidence 草稿 |
| close | 待验收 | 已关闭 | **必须**非空 evidence_note；隐患 → 已闭环 |
| reject | 待验收 | 执行中 | 可附驳回说明；隐患 → 整改中 |

同一隐患同时只允许一张未关闭整改单。

### 4.3 AuditEvent

- `id`、`ts`、`tenant_id`、`role`、`actor`（可与 role 相同或预留）
- `action`：如 `ticket.create` / `ticket.advance` / `ticket.denied`
- `target_type` / `target_id`
- `payload_json`：措施摘要、from→to、证据是否提供（不存密钥）
- `ok`：bool；`error`：拒绝原因

只追加，不更新、不删除。

## 5. API（REST）

前缀 `/api`，皆需身份。

- `GET /health`
- `GET /api/hazards` — 查询参数：status、level、plant、keyword
- `GET /api/hazards/{id}`
- `GET /api/tickets` — hazard_id、status
- `POST /api/tickets` — body: hazard_id, measures, owner?, due_days?；写权限
- `POST /api/tickets/{id}/advance` — body: action, evidence_note?；写权限 + 状态机
- `GET /api/audit` — limit、action?；viewer **403**；engineer/admin 本租户

错误：400 业务规则；403 权限/租户；404 不存在。响应 JSON，`detail` 为可读中文。

## 6. UI

单页「领域台账」：

1. 顶栏：租户、角色切换（便于演示隔离）
2. 左：隐患列表 + 筛选
3. 中：选中隐患详情 +「开整改单」表单
4. 右或下方：该隐患整改单时间线 + 推进按钮（按当前态只亮合法 action）
5. 底部或抽屉：审计列表（viewer 显示无权限提示）

关闭时弹窗强制填写证据，空内容不可提交。

## 7. 测试与课记

- `tests/test_capa_state_machine.py`、`test_acl_audit.py`、`test_domain_api.py`
- 课记路径：`docs/lessons/ch1-domain.md`（重做后编号从 Ch1 重新计）
- README：仅 Ch1 启动方式（backend uvicorn + frontend dev）

## 8. 清库与重做顺序

1. 本规格用户审阅通过  
2. 在 **1:1** 授权下将 `main` force-push 为仅含 README + 本规格（或等价空壳）  
3. 写实现计划（writing-plans）  
4. 按计划实现 Ch1 → pytest 绿 → 课记 → push  

## 9. 后续章节（占位，不实现）

- Ch2：Agent 循环 + 工具仅调本领域 API  
- Ch3：SSE / 可观测  
- 其后：durable run、HITL、eval、Compose/Postgres  

---

审阅焦点：DoD 是否够严、状态机是否要加态、审计字段是否缺「面试常问」项。
