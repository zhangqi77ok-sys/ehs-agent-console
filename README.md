# ehs-agent-console

EHS 领域台账控制台（Ch1）。**无 Agent / LLM / SSE**——领域 DoD 完成前不上 Agent。

- 规格：[`docs/superpowers/specs/2026-10-13-ehs-domain-ch1-design.md`](docs/superpowers/specs/2026-10-13-ehs-domain-ch1-design.md)
- 计划：[`docs/superpowers/plans/2026-10-13-ehs-domain-ch1.md`](docs/superpowers/plans/2026-10-13-ehs-domain-ch1.md)
- 课记：[`docs/lessons/ch1-domain.md`](docs/lessons/ch1-domain.md)
- 大纲：[`docs/curriculum.md`](docs/curriculum.md)

## 快速启动（Ch1）

### 后端

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

默认 SQLite：`DATABASE_URL=sqlite:///./data/ehs.db`（启动时 Alembic migrate + 种子隐患）。

身份头：`X-Tenant-Id`、`X-Role`（`viewer` | `ehs_engineer` | `admin`）。

### 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://127.0.0.1:5173 。Vite 将 `/api`、`/health` 代理到 `:8000`。

演示路径：查隐患 → 开整改单 → start → submit_verify → close（填证据）→ 看审计；切换 viewer / 其他租户验证隔离。

### 测试

```bash
cd backend && source .venv/bin/activate && pytest -q
cd ../frontend && npm run build
```

## Ch1 DoD

1. CAPA 状态机 + 关闭必须证据  
2. viewer 只读；engineer 可写；跨租户隔离  
3. 写操作与拒绝均写 `audit_events`  
4. 可点领域 UI（无聊天页）  
5. pytest 绿 · `npm run build` 通过 · 中文课记  
