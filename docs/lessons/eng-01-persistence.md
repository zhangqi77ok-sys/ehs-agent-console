# Eng-01 · 持久化与迁移（成都 20–30K 工程补强①）

## 做了什么

内存台账改为 **SQLAlchemy** 落库；默认 `sqlite:///./data/ehs.db`，可用 `DATABASE_URL` 切 Postgres。

- 表：`hazards` / `tickets` / `chat_sessions` / `chat_messages`
- 迁移：Alembic `alembic/versions/c77c3222da08_*.py`
- 启动：`lifespan` → `init_db` + `seed_if_empty`
- 工具层仍走 `hazard_ledger` facade → `app/db/repo.py`
- 会话写入数据库（重启不丢，进程内文件库）

## 跟练（PowerShell）

```powershell
cd F:\ehs-agent-console
git pull
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# 可选：alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

验收操作：

1. `GET /health` 含 `"persistence":"sqlalchemy"`、`hazard_count`≥12  
2. 开一张整改单后，**重启 uvicorn**，`GET /api/tickets` 仍能看到该单  
3. `POST /api/sessions` 后查库或再 `GET /api/sessions/{id}` 存在  
4. `alembic history` 能看到 eng1 revision  

切 Postgres（可选）：`.env` 设  
`DATABASE_URL=postgresql+psycopg://user:pass@host/db`  
后执行 `alembic upgrade head`。

## 验收清单（Definition of Done）

- [ ] 依赖含 sqlalchemy / alembic，README/课记写明  
- [ ] 有可重复的 migration，而不是只靠 create_all  
- [ ] 隐患/整改单/会话均在 DB，重启后数据仍在  
- [ ] 领域 API 与 Agent 工具读写同一套库  
- [ ] `.db` 文件已 gitignore，不提交密钥与本地库  

通过后进入 **Eng-02：pytest + CI**。
