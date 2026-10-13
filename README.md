# EHS 隐患闭环 Agent 控制台（v2 重写中）

> 作品集项目：先把 **EHS 领域**做硬，再叠 **手写 Agent 循环** 与可视化控制台。  
> 当前进度：**第 1 章 · 领域底座**（台账 + 整改单状态机 + REST + 素控制台）。

旧版「一周堆完」课记已归档到 [`docs/lessons/_archive/v1/`](docs/lessons/_archive/v1/)。课纲见 [`docs/curriculum.md`](docs/curriculum.md)。

## 第 1 章你能演示什么

- 12 条跨车间隐患（消防/电气/机械/危化/动火/有限空间/环保…），含重大、逾期、待验收
- 整改单状态机：待执行 → 执行中 → 待验收 → 已关闭（与台账联动；已闭环拒开单）
- REST：`/api/hazards`、`/api/tickets`、`/api/tickets/{id}/advance`、`/api/domain/summary`
- 前端：表格 + 开单/推进表单（**不依赖聊天**）

Agent / SSE / RAG / 评测门禁：代码仍在仓库里，但**教学主线从第 2 章起按新标准重做**，不以旧课记为准。

## 配置

```powershell
cd F:\ehs-agent-console\backend
copy .env.example .env
# 第 1 章跟练领域可不配 LLM；第 2 章起再配 OPENAI_* 
```

## 本地运行（PowerShell）

```powershell
# 后端
cd F:\ehs-agent-console\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端（另开终端）
cd F:\ehs-agent-console\frontend
npm install
npm run dev
```

健康检查：<http://127.0.0.1:8000/health>（应含 `"chapter": 1`）

## 课记

- [01 · 领域底座](docs/lessons/01-domain.md)

## License

MIT
