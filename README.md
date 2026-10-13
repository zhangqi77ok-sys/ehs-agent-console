# ehs-agent-console

EHS 领域台账 + 手写 Agent Runtime（**Ch1–Ch22**）。面向成都 Agent 应用/后端（约 20–30k）作品集：**课记可追问 · Demo 真串得起来 · 工程非贴皮**。

> 诚实声明：任何仓库都不能保证面试成功或 offer；本仓把高频技术点做到可演示、可指代码，并附模拟面试、失败演练与 Practice 自评。口语、真 LLM 临场、公司匹配仍是你的变量。

## 导航

| 文档 | 说明 |
|------|------|
| [`docs/curriculum.md`](docs/curriculum.md) | 大纲 Ch1–22 |
| [`docs/readiness-scorecard.md`](docs/readiness-scorecard.md) | 技术维度诚实评分（非 offer 概率） |
| [`docs/architecture.md`](docs/architecture.md) | Runtime 架构一页纸（mermaid） |
| [`docs/jd-gap-matrix.md`](docs/jd-gap-matrix.md) | JD 关键词 → 路径/Demo |
| [`docs/demo-script.md`](docs/demo-script.md) | 10 分钟 Demo |
| [`docs/oral-15min.md`](docs/oral-15min.md) | 15 分钟口述 |
| [`docs/mock-interview.md`](docs/mock-interview.md) | 30 问模拟面试 |
| [`docs/practice-rubric.md`](docs/practice-rubric.md) | Practice 三档评分 |
| [`docs/eval-dashboard.md`](docs/eval-dashboard.md) | 多维 Eval 最近一次表（跑 eval 生成） |
| [`docs/failure-mode-drill.md`](docs/failure-mode-drill.md) | 超时/HITL/跨租户演练 |
| [`docs/interview.md`](docs/interview.md) | 追问稿 |
| [`docs/resume-project.md`](docs/resume-project.md) | STAR 简历段 |

## 快速启动

```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
LLM_PROVIDER=mock uvicorn app.main:app --reload --port 8000

cd frontend && npm install && npm run dev
```

浏览器 http://127.0.0.1:5173 ：**Domain** / **Agent** / **Runtime**（含可观测摘要） / **Practice**。

身份：`X-Tenant-Id` / `X-Role`，或 `POST /auth/token`（JWT），或 `X-API-Key: demo-key`。响应带 `X-Request-Id`。

### 测试 / Eval

```bash
cd backend && source .venv/bin/activate && pytest -q
LLM_PROVIDER=mock python scripts/run_eval.py -v
```

### Compose（pgvector 镜像）

```bash
cp .env.example .env && docker compose up --build
```

## 能力快览

- **Ch1** 隐患 + CAPA + ACL + 审计 + UI  
- **Ch2–5** 手写循环 · SSE · Durable · HITL · Trace  
- **Ch6–7** Mock Eval · Compose · 面试稿  
- **Ch8** JWT/API Key · JSON access log  
- **Ch9** 法规 RAG（切块 + 本地 embedding + score）  
- **Ch10** Session 记忆压缩  
- **Ch11** Supervisor → Investigator/Clerk（工具白名单 + 双时间线）  
- **Ch12** 就业包与模拟面试  
- **Ch13** `/api/obs/summary` · `/metrics` · spans 导出 · failure_mode UI  
- **Ch14** Postgres/`regulation_chunks` RAG 路径（sqlite 回退）  
- **Ch15** MCP 风格 tools list + call（薄层）  
- **Ch16** 多维 Eval + dashboard  
- **Ch17** Practice 面试练习模式  
- **Ch18** OTLP HTTP JSON 可选导出  
- **Ch19** JWKS / OIDC-lite 验签  
- **Ch20** 并行 Multi-Agent + parallel 徽章  
- **Ch21** 可选 Live LLM Eval（默认 skip）  
- **Ch22** 就绪评分卡  
