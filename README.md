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
| 可视化（SSE） | 左侧对话，右侧**实时**刷步骤 / 工具 / 预算（`POST /api/chat`） |
| 可靠性 | LLM/工具超时 + 退避重试；前端「强制超时」练习 |
| 评测门禁 | `backend/eval/cases.json` + `scripts/run_eval.py`（真实 LLM） |
| Demo 打磨 | 顶栏健康/预算/评测 chip；预算熔断着色；错误可行动提示 |

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
docs/lessons/     每次改动的中文教学文档（跟练用）
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

## 流式步骤（SSE）

前端默认走 `POST /api/chat`（`text/event-stream`）。事件顺序大致为：

`budget` → `step_start` → `tool_call` → `tool_result` → … → `final` → `done`

右栏在收到 `tool_call` / `tool_result` / `final` 时立刻追加，不必等整轮结束。脚本或 curl 可用非流式：`POST /api/chat/complete`。

## 面试可以怎么讲

完整讲法（30 秒故事、架构、Q&A、Demo 剧本）见 **[docs/interview.md](docs/interview.md)**。

速记：

1. **问题**：EHS 现场要查台账、开单、对照制度，人工慢且难追踪 Agent 决策过程。
2. **方案**：手写 ReAct 风格循环；工具边界清晰；SSE 把每一步暴露出来（可观测）。
3. **取舍**：默认真实模型；台账先内存示例；RAG 先做关键词 stub，Week2 换向量库。
4. **工程信号**：步数预算熔断、超时退避重试、5 条评测脚本门禁、控制台状态/错误可行动。

更细的设计见 [docs/architecture.md](docs/architecture.md)。

## Week1 进度

| Day | 内容 | 状态 |
|-----|------|------|
| 1–2 | 脚手架 + 真实 LLM + SSE 步骤可视化 | ✅ |
| 3 | `list_open_hazards` 工具 | ✅ |
| 4 | 超时/重试 + 前端强制超时练习 | ✅ |
| 5 | 评测集门禁（5 cases） | ✅ |
| 6 | 控制台打磨（状态栏/预算熔断/错误文案/评测露出） | ✅ |
| 7 | [面试讲法](docs/interview.md) | ✅ |

## 教学文档

每次代码改动都会写一篇中文教学文档（目标、关键代码、跟练、思考题），目录见 [docs/lessons/](docs/lessons/README.md)。

- [01 · SSE 流式步骤](docs/lessons/01-sse-agent-steps.md)
- [02 · 给 Agent 加新工具](docs/lessons/02-add-agent-tool.md)
- [03 · 超时与重试](docs/lessons/03-timeout-retry.md)
- [04 · 前端「强制超时」练习](docs/lessons/04-frontend-timeout-drill.md)
- [05 · 评测集（门禁）](docs/lessons/05-eval-set.md)
- [06 · 控制台打磨](docs/lessons/06-polish.md)
- [07 · 面试复盘](docs/lessons/07-interview.md) → 主文 [docs/interview.md](docs/interview.md)

## 评测门禁（Week1 Day5）

固定 5 条业务用例，走与 UI 相同的 `run_agent`（真实 LLM），断言工具名 + 回答关键词；挂了非零退出码。

```bash
cd backend
source .venv/bin/activate
python scripts/run_eval.py -v
# 单条：python scripts/run_eval.py --only list_open_hazards
```

说明见 [docs/lessons/05-eval-set.md](docs/lessons/05-eval-set.md)。

## License

MIT
