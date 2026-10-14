# ehs-agent-console

**最终版（一次看完）→ [docs/最终版-保姆级全书.md](docs/最终版-保姆级全书.md)**  
（保姆级、大白话、从装环境到三句话收口，一整本滚完即可。）

可选：[想拆天练也可以 → docs/跟我学/](docs/跟我学/README.md)

EHS 领域台账 + 手写 Agent Runtime（Ch1–Ch22）。人可以在网页改隐患/整改单；AI 助手也能查、也能帮开单——但改数据走同一套规矩。

## 快速启动

```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
LLM_PROVIDER=mock uvicorn app.main:app --reload --port 8000

cd frontend && npm install && npm run dev
```

浏览器 http://127.0.0.1:5173 ：**Domain 台账** / **Agent** / **Runtime**。

更细的安装步骤（含 Windows PowerShell）见 [最终版全书 · 第 0 章](docs/最终版-保姆级全书.md)。

### 测试（可选）

```bash
cd backend && source .venv/bin/activate && pytest -q
LLM_PROVIDER=mock python scripts/run_eval.py -v
```

### Compose（可选）

```bash
cp .env.example .env && docker compose up --build
```

## 文档怎么放

| 你想… | 去哪 |
|------|------|
| **一次看完** | **[最终版保姆级全书](docs/最终版-保姆级全书.md)** ← 主入口 |
| 拆天练 | [跟我学](docs/跟我学/README.md)（可选） |
| 查某章细节 | [课记词典](docs/lessons/README.md)（全书摸完再用） |
| 看架构一页纸 | [architecture.md](docs/architecture.md) |
| 大纲 Ch1–22 | [curriculum.md](docs/curriculum.md) |
| 面试材料 | [面试备用](docs/面试备用/)（**先别看**，摸完全书再说） |

门口旧链：[保姆级入门](docs/保姆级入门.md)（只指向最终版）。
