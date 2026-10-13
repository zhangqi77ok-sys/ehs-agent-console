# Ind-05 · Docker Compose + Postgres（可交付形态）

## 为什么要做（对齐 JD）

成都 20–30K Agent 应用/后端岗常问：**「本地 SQLite Demo 怎么变成同事能 `compose up` 的交付物？」**  
SQLite 适合单测与本机跟练；面试官要听的是：

| 能力 | 本仓库对应 |
|------|------------|
| 与生产同形的依赖拓扑 | `docker-compose.yml`：`db` + `api` + `web` |
| 关系库不是玩具 | Postgres 16 + 命名卷 + healthcheck |
| 迁移进启动路径 | 容器入口 `alembic upgrade head` 再起 uvicorn |
| 全栈一键可看 | nginx 反代 `/api`、`/health`，SSE 关缓冲 |

诚实口径：Compose ≠ K8s；但比「只有本机 `.db`」更能证明你做过**可交付边界**。

## 做了什么

1. **根目录 `docker-compose.yml`**：`db`（Postgres 16）、`api`（backend 镜像）、`web`（Vite build + nginx）。
2. **`backend/Dockerfile` + `docker-entrypoint.sh`**：Python 3.12 → 装依赖 → **先迁移再 uvicorn**。
3. **`frontend/Dockerfile` + `docker/nginx.conf`**：多阶段构建；`/api`、`/health` 反代到 `api:8000`；SSE `proxy_buffering off`。
4. **驱动**：`psycopg[binary]`（同步，匹配现有 `SessionLocal`）；URL 形如 `postgresql+psycopg://...`。
5. **默认仍 SQLite**：`app/config.py` / 本机 pytest 不强迫 Docker。
6. **冒烟**：`scripts/smoke_compose.sh`（需本机 Docker）；`tests/test_postgres_optional.py` 仅在 `DATABASE_URL` 为 postgres 时跑。

## 跟练

### A. 一键全栈（推荐演示）

```powershell
cd F:\ehs-agent-console
git pull
copy .env.example .env
# 按需改 POSTGRES_PASSWORD / OPENAI_*；演示可用 LLM_PROVIDER=mock
docker compose up -d --build
```

验收：

1. `curl http://127.0.0.1:8000/health` → `"status":"ok"`、`"persistence":"sqlalchemy"`
2. 浏览器打开 http://127.0.0.1:5173 → 台账 / Agent / Runtime 可点
3. `docker compose exec api alembic current` 能看到 head revision

停掉：`docker compose down`（保留卷）。**清库**：`docker compose down -v`（会删 Postgres 数据，慎用）。

冒烟脚本（Linux/macOS / Git Bash）：

```bash
./scripts/smoke_compose.sh
```

### B. 本机 uvicorn + 仅 Postgres 容器

```powershell
docker compose up -d db
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL="postgresql+psycopg://ehs:ehs_change_me@127.0.0.1:5432/ehs"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

pytest 默认仍走 SQLite（勿把 compose 的 DATABASE_URL 写进会污染单测的全局 `.env` 除非你清楚后果）。

### C. 纯本机 SQLite（跟练 / CI）

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:LLM_PROVIDER="mock"
pytest -q
```

## 坑点（面试也能讲）

1. **迁移时机**：镜像启动必须 `alembic upgrade head`，不能只靠 `create_all`（生产会漂移）。
2. **卷误删**：`down -v` 抹掉 `ehs_pgdata`，Run/审批/台账全没——演示前先说清。
3. **URL 驱动前缀**：SQLAlchemy 2 + psycopg3 用 `postgresql+psycopg://`，不是旧的 `psycopg2` 默认串。
4. **SSE 反代**：nginx 默认缓冲会「卡住」Agent 流式；本仓库已关 `proxy_buffering`。
5. **密钥**：`.env` gitignore；示例密码仅本地，投产务必改 `POSTGRES_PASSWORD` / `JWT_SECRET`。
6. **本机无 Docker**：文件与课记仍可交；在有 Docker 的机器跑 `smoke_compose.sh` 再录屏。

## 验收清单

- [ ] 根目录有 `docker-compose.yml`，含 db / api /（建议）web
- [ ] `backend/Dockerfile` 启动路径含 Alembic
- [ ] `requirements.txt` 含 `psycopg[binary]`；默认 DATABASE_URL 仍为 sqlite
- [ ] `.env.example` 文档化 Compose 变量
- [ ] `LLM_PROVIDER=mock pytest -q` 绿（不依赖 Docker）
- [ ] 有 Docker 时：`docker compose up` 后 `/health` ok
- [ ] 课记 + curriculum Ind-05 ✅ + README 一键说明

下一章 **Ind-06：工具策略与审计日志**。
