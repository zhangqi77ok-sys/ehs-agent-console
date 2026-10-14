# ehs-agent-console

**从这里开始 → [docs/跟我学/README.md](docs/跟我学/README.md)**  
（保姆级、按天点、一次只一天。Day1 做完就停。）

EHS 领域台账 + 手写 Agent Runtime（Ch1–Ch22）。人可以在网页改隐患/整改单；AI 助手也能查、也能帮开单——但改数据走同一套规矩。

## 快速启动

```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
LLM_PROVIDER=mock uvicorn app.main:app --reload --port 8000

cd frontend && npm install && npm run dev
```

浏览器 http://127.0.0.1:5173 ：**Domain 台账** / **Agent** / **Runtime**。

更细的安装步骤见 [Day0](docs/跟我学/Day0-装环境.md)。

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
| 跟着学 | **[跟我学](docs/跟我学/README.md)** ← 唯一主路径 |
| 查某章细节 | [课记词典](docs/lessons/README.md)（Day7 后再用） |
| 看架构一页纸 | [architecture.md](docs/architecture.md) |
| 大纲 Ch1–22 | [curriculum.md](docs/curriculum.md) |
| 面试材料 | [面试备用](docs/面试备用/)（**先别看**，跟完七天再说） |

门口旧链：[保姆级入门](docs/保姆级入门.md)（只指向跟我学）。
