# EHS 隐患闭环 Agent 控制台（v2）

Python FastAPI **手写 Agent 循环** + Vite/React（领域台账页 + Agent SSE 页）。  
课纲 1–9 章已按新标准落地，详见 [`docs/curriculum.md`](docs/curriculum.md)。

## 能力一览

| 章 | 能力 |
|----|------|
| 1 | 隐患/整改单状态机 + REST + 素台账页 |
| 2–3 | 手写循环 + SSE 左聊右步骤 |
| 4 | 超时/重试/预算 + 强制超时练习 |
| 5 | `python scripts/run_eval.py` 门禁 |
| 6 | 法规 FAISS RAG（网关嵌入优先，TF-IDF 兜底） |
| 7 | 服务端 session 多轮 |
| 8 | 租户 / 角色请求头权限雏形 |
| 9 | [面试讲法](docs/interview.md) |

持久化：默认 SQLite（`DATABASE_URL`），Alembic 迁移见 `backend/alembic/`，课记 [Eng-01](docs/lessons/eng-01-persistence.md)。

## 运行（PowerShell）

```powershell
cd F:\ehs-agent-console
git pull

cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # 填写 OPENAI_API_KEY / BASE_URL / MODEL
python scripts\build_rag_index.py --force
uvicorn app.main:app --reload --port 8000

# 另开终端
cd F:\ehs-agent-console\frontend
npm install
npm run dev
```

健康检查：http://127.0.0.1:8000/health  

评测：`python scripts\run_eval.py -v`

## License

MIT
