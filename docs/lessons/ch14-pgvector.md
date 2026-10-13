# Ch14 课记：Postgres / pgvector RAG 路径

## 交付

- Compose DB 镜像改为 `pgvector/pgvector:pg16`
- 迁移 `0004_ch14_rag`：`regulation_chunks`（`embedding_json` 通用；Postgres 尽力加 `vector(256)`）
- `rag/pg_store.py`：`DATABASE_URL` 为 postgres 时走表存储；sqlite 仍用内存索引
- 工具 `search_regulations` 经 `get_active_regulations_store()` 自动切换
- 无 Postgres 时 pytest **跳过** 在线同步测例

## 如何切换

```bash
# 本地演示（默认 sqlite 内存 RAG）
LLM_PROVIDER=mock uvicorn app.main:app --reload

# Compose / 真 Postgres
docker compose up --build
# API 容器 DATABASE_URL=postgresql+psycopg://...
# 首次 search 会 sync markdown → regulation_chunks
```

可选强化（文档级，非强制）：`ALTER TABLE ... SET embedding = embedding_json::vector` + `ivfflat` 索引。

## 面试官追问（≥5）

**Q1：为何 embedding 先存 JSON？**  
A：sqlite 测试与 CI 无 pgvector 扩展；JSON 保证可测。Postgres 上再挂 vector 列。

**Q2：和 Ch9 内存库什么关系？**  
A：Ch9 是切块+hash embed+余弦；Ch14 把同一向量**持久化**到 DB，切换点是 URL dialect。

**Q3：生产还缺什么？**  
A：真 embedding 模型、ANN 索引调参、租户级语料隔离、增量更新。面试主动说。

**Q4：为何 cosine 仍在 Python？**  
A：小语料够用且跨库一致；上 pgvector 后可改 `ORDER BY embedding <=> :q`。

**Q5：迁移里 CREATE EXTENSION 失败怎么办？**  
A：best-effort；JSON 路径仍可用。Compose 已换 pgvector 镜像降低失败率。

**Q6：如何证明「切到 postgres」？**  
A：命中结果带 `"backend": "postgres"`；或查 `regulation_chunks` 行数。
