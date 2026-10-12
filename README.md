# EHS 隐患闭环 Agent 控制台

> 作品集项目：用 **Python FastAPI 手写 Agent 循环** + **Vite/React 可视化控制台**（左聊天 / 右步骤·工具·预算），演示 EHS 隐患查询、开整改单、法规摘要检索。

默认走 **真实 OpenAI 兼容 LLM**（需配置 `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL`）。仅离线演示时可显式设 `LLM_PROVIDER=mock`。

## 动机

- Agent 应用岗默认要求 Python + 工具调用 + RAG + 可观测。
- 结合本人 EHS 业务背景，做一个**能写进简历的垂直域 Agent**，比泛化聊天机器人更有说服力。
- 先手写循环，再谈框架——面试能讲清底层机制。

## 功能（MVP）

| 能力 | 说明 |
|------|------|
| 查隐患台账 | `query_hazard_ledger`（内存示例数据） |
| 开整改单 | `create_corrective_ticket` |
| 法规摘要 | `search_regulations`（对样例 markdown 做关键词 stub） |
| 可视化 | 左侧对话，右侧步骤 / 工具参数与结果 / 步数预算 |

试试这些问题：

- 「查一下灭火器相关隐患」
- 「有哪些重大隐患？」
- 「给 HZ-2026-001 开整改单，措施：更换过期灭火器」
- 「隐患闭环的法规要求是什么？」

## 目录

```
backend/          FastAPI + Agent 循环 + 工具
frontend/         Vite + React 控制台
docs/architecture.md
```

## 配置（必填）

```bash
cd backend
cp .env.example .env
# 编辑 .env：
# LLM_PROVIDER=openai          # 默认；离线才设 mock
# OPENAI_API_KEY=sk-...
# OPENAI_BASE_URL=http://HOST:7863/v1   # 须含 /v1；或 https://api.openai.com/v1
# OPENAI_MODEL=glm-5.3-flash            # 网关实际模型名
```

`.env` 已在 `.gitignore` 中，**切勿提交密钥**。缺 Key / Base URL 时接口会返回明确错误，不会静默降级到 mock。

## 本地运行

### 1. 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

健康检查：<http://127.0.0.1:8000/health>

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

打开 Vite 提示的地址（默认 <http://127.0.0.1:5173>）。开发服务器已把 `/api` 代理到后端。

### 一键心智模型

```bash
# 终端 A
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
# 终端 B
cd frontend && npm run dev
```

## 面试可以怎么讲

1. **问题**：EHS 现场要查台账、开单、对照制度，人工慢且难追踪 Agent 决策过程。
2. **方案**：手写 ReAct 风格循环；工具边界清晰；前端把每一步暴露出来（可观测）。
3. **取舍**：默认真实模型；台账先内存示例；RAG 先做关键词 stub，Week2 换向量库。
4. **工程背景**：后端拆分、接口契约、预算熔断（最大步数）——Java/企业级经验迁到 Python Agent。

更细的设计见 [docs/architecture.md](docs/architecture.md)。

## License

MIT
