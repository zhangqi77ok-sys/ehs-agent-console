# ehs-agent-console

EHS 领域台账 + 手写 Agent Runtime（**Ch1–Ch8 完成**（就业补强进行中））。工具只调领域层（CAPA / ACL / 审计），不旁路。

- 大纲：[`docs/curriculum.md`](docs/curriculum.md)
- 面试：[`docs/interview.md`](docs/interview.md) · 简历：[`docs/resume-project.md`](docs/resume-project.md)
- Ch1 规格：[`docs/superpowers/specs/2026-10-13-ehs-domain-ch1-design.md`](docs/superpowers/specs/2026-10-13-ehs-domain-ch1-design.md)

## 快速启动

```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
LLM_PROVIDER=mock uvicorn app.main:app --reload --port 8000

cd frontend && npm install && npm run dev
```

浏览器 http://127.0.0.1:5173 ：**Domain** / **Agent** / **Runtime**。

身份：演示仍可用头 `X-Tenant-Id` / `X-Role`；也支持 `POST /auth/token` 发 JWT，或 `X-API-Key: demo-key`。响应带 `X-Request-Id`。

### 测试 / Eval

```bash
cd backend && source .venv/bin/activate && pytest -q
LLM_PROVIDER=mock python scripts/run_eval.py -v
```

### Compose

```bash
cp .env.example .env && docker compose up --build
```
