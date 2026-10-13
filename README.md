# ehs-agent-console

EHS 领域台账 + 手写 Agent Runtime（Ch1–Ch7）。工具只调领域层（CAPA / ACL / 审计），不旁路。

- 大纲：[`docs/curriculum.md`](docs/curriculum.md)
- Ch1 规格：[`docs/superpowers/specs/2026-10-13-ehs-domain-ch1-design.md`](docs/superpowers/specs/2026-10-13-ehs-domain-ch1-design.md)

## 快速启动

```bash
# 后端（默认 LLM_PROVIDER=mock）
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend && npm install && npm run dev
```

打开 http://127.0.0.1:5173 ：**Domain** 台账 / **Agent** 对话 / **Runtime**（durable run · HITL）。

身份头：`X-Tenant-Id`、`X-Role`（`viewer` | `ehs_engineer` | `admin`）。

可选真 LLM：`LLM_PROVIDER=openai OPENAI_API_KEY=... OPENAI_BASE_URL=...`

### 测试

```bash
cd backend && source .venv/bin/activate && pytest -q
cd ../frontend && npm run build
```

### Compose（Ch6）

```bash
docker compose up --build
```
