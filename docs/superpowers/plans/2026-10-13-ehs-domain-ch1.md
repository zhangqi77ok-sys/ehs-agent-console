# Ch1 领域台账 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从空壳重建可点的 EHS 领域台账（隐患 + 整改单状态机 + 角色隔离 + 写审计 + 验收证据），无 Agent。

**Architecture:** FastAPI 领域 REST + SQLAlchemy/Alembic/SQLite；Vite/React 单页领域 UI；身份经统一 deps 解析 `X-Tenant-Id`/`X-Role`；所有写路径写 `audit_events`。

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, pytest, Vite, React

**Spec:** `docs/superpowers/specs/2026-10-13-ehs-domain-ch1-design.md`

## Global Constraints

- Domain-first：本计划 **禁止** 引入 Agent/LLM/SSE/HITL/Eval/RAG
- 课记必须中文、面试可追问；测绿才宣称完成并 push
- 默认 `DATABASE_URL=sqlite:///./data/ehs.db`；不强制 Compose
- 关闭整改单必须非空 `evidence_note`；viewer 只读；跨租户 403
- 清库后从空壳实现；保留规格文件与本计划

---

## File map（清库后新建）

```
backend/
  app/main.py
  app/config.py
  app/db/{base,session,models,seed,repo}.py
  app/auth/{deps,tenant}.py
  app/api/{health,domain,audit}.py
  app/domain/capa.py          # 状态机纯函数
  alembic/ + versions/
  tests/{conftest,test_capa_state_machine,test_acl_audit,test_domain_api}.py
  requirements.txt
frontend/
  src/{App.jsx,main.jsx,styles.css,api/domain.js,components/DomainPanel.jsx}
docs/lessons/ch1-domain.md
README.md                     # 仅 Ch1 启动
```

---

### Task 1: 后端骨架 + 健康检查

**Files:**
- Create: `backend/requirements.txt`, `backend/app/__init__.py`, `backend/app/main.py`, `backend/app/config.py`, `backend/app/api/health.py`
- Test: `backend/tests/conftest.py`, `backend/tests/test_health.py`

**Interfaces:**
- Produces: `create_app()` → FastAPI；`GET /health` → `{ok: true}`

- [ ] **Step 1:** 写失败测试 `test_health_ok`（TestClient get `/health` expect 200）
- [ ] **Step 2:** 实现最小 FastAPI app + `/health`
- [ ] **Step 3:** `pytest -q` 绿
- [ ] **Step 4:** Commit `chore(ch1): backend skeleton + health`

---

### Task 2: 模型 + Alembic + 种子数据

**Files:**
- Create: `backend/app/db/models.py` (Hazard, Ticket, AuditEvent + tenant_id)
- Create: Alembic env + revision `0001_ch1_domain`
- Create: `backend/app/db/seed.py`（至少 4 条隐患，含重大/一般、可开单）
- Modify: `main.py` lifespan：create tables or `alembic upgrade head` + seed if empty

**Interfaces:**
- Produces: ORM models；`seed_if_empty(session)`

- [ ] **Step 1:** 写测试：空库 seed 后 `GET` 隐患数 ≥ 4（可先 skip 到 Task 3 API；本任务用 repo 直测）
- [ ] **Step 2:** 实现 models + migration + seed
- [ ] **Step 3:** 本地 `alembic upgrade head` 成功
- [ ] **Step 4:** Commit `feat(ch1): hazards/tickets/audit models + seed`

---

### Task 3: CAPA 状态机纯函数（TDD）

**Files:**
- Create: `backend/app/domain/capa.py`
- Test: `backend/tests/test_capa_state_machine.py`

**Interfaces:**
- Produces: `transition(status: str, action: str) -> tuple[str, str | None]`  
  返回 `(new_status, error)`；合法映射见规格 §4.2  
- Produces: `require_evidence_for_close(action, evidence_note) -> str | None` 错误信息

- [ ] **Step 1:** 写失败测试：四条合法迁移 + 非法迁移报错 + close 无证据报错
- [ ] **Step 2:** 实现 `capa.py`
- [ ] **Step 3:** pytest 绿
- [ ] **Step 4:** Commit `feat(ch1): CAPA transition pure functions`

---

### Task 4: 身份 + 角色 ACL

**Files:**
- Create: `backend/app/auth/tenant.py`, `backend/app/auth/deps.py`
- Test: `backend/tests/test_acl_audit.py`（先测 allow/deny 函数）

**Interfaces:**
- Produces: `ROLES`；`resolve_identity(headers) -> dict`；`domain_can_write(role) -> bool`
- Consumes: headers `X-Tenant-Id`, `X-Role`

- [ ] **Step 1:** 测试 viewer 不可写、engineer 可写、未知角色回落
- [ ] **Step 2:** 实现 tenant/deps
- [ ] **Step 3:** pytest 绿
- [ ] **Step 4:** Commit `feat(ch1): tenant role ACL helpers`

---

### Task 5: Repo + 领域 API + 审计写入

**Files:**
- Create: `backend/app/db/repo.py`, `backend/app/api/domain.py`, `backend/app/api/audit.py`
- Modify: `main.py` include routers
- Test: `backend/tests/test_domain_api.py`, 扩展 `test_acl_audit.py`

**Interfaces:**
- Produces REST（规格 §5）：hazards CRUD-list、tickets create/advance、audit list
- 每次 create/advance/denied 调用 `repo.append_audit(...)`

- [ ] **Step 1:** 失败测试：开单、非法迁移 400、viewer POST 403、跨租户 403、close 无证据 400、成功 close 后审计增加且含 evidence 标记
- [ ] **Step 2:** 实现 repo + routers；审计在写路径与拒绝路径都写
- [ ] **Step 3:** `LLM_PROVIDER` 无关；`pytest -q` 全绿
- [ ] **Step 4:** Commit `feat(ch1): domain REST + audit trail`

---

### Task 6: 前端领域台账 UI

**Files:**
- Create: frontend Vite React 工程（若空壳）；`DomainPanel.jsx`、`api/domain.js`、`App.jsx`、`styles.css`
- 无 Chat/Agent tab

**Interfaces:**
- Consumes: 上述 REST + 顶栏切换 tenant/role

- [ ] **Step 1:** 搭 Vite 应用，代理 `/api` `/health` 到 8000
- [ ] **Step 2:** 实现列表/开单/推进/证据弹窗/审计抽屉
- [ ] **Step 3:** 手动点通：开单→start→submit_verify→close（填证据）；viewer 切角色看不到写按钮且审计 403 提示
- [ ] **Step 4:** `npm run build` 成功；Commit `feat(ch1): domain console UI`

---

### Task 7: 课记 + README + DoD 门禁

**Files:**
- Create: `docs/lessons/ch1-domain.md`
- Modify: `README.md`（仅 Ch1 启动）
- Modify: `docs/curriculum.md`（新建，Ch1 ✅，Ch2+ 占位禁止开工）

- [ ] **Step 1:** 课记写清：状态机表、为何 close 要证据、审计面试怎么答、复现步骤
- [ ] **Step 2:** 对照规格 §2 DoD 逐条勾选，全部满足
- [ ] **Step 3:** Commit `docs(ch1): lesson + README DoD`
- [ ] **Step 4:** Push `main`

---

## Execution notes

1. **先决：** 1:1 force-push 清空 `main`，仅留 README + spec（+ 本 plan 若已存在则一并保留）。
2. 实现时用 subagent-driven-development，每 Task 测绿再下一 Task。
3. 旧 Ind/Eng/Agent 代码不得复用粘贴成「贴皮」；允许参考行为，必须按本计划新建边界清晰的文件。
