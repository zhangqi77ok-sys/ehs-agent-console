# Ch9 课记：法规 / 制度 RAG

## 面试怎么讲

1. **为什么要 RAG**：EHS 开单要对照制度期限与证据要求；把规章塞进 prompt 会爆上下文且难更新。切块入库 + 检索工具更稳。
2. **本仓怎么做**：`data/regulations/*.md` → 按 `##` 切块 → **本地 hashing embedding**（无外网也可跑）→ 余弦检索 → 工具 `search_regulations`。
3. **和领域的边界**：RAG 只读制度，不改台账；真正开单/关单仍走 CAPA + 审计。
4. **诚实差距**：未接真 embedding API / 向量库（FAISS/pgvector）；未做权限分级文档；rerank / citation 校验可继续加深。

## 路径

- `app/rag/{chunk,embed,store}.py`
- 工具：`search_regulations`（registry + mock eval case）
