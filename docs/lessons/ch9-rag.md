# Ch9 课记：法规 / 制度 RAG

## 面试怎么讲

1. **为什么要 RAG**：EHS 开单要对照制度期限与证据要求；把规章塞进 prompt 会爆上下文且难更新。切块入库 + 检索工具更稳。
2. **本仓怎么做**：`data/regulations/*.md` → 按 `##` 切块 → **本地 hashing embedding**（无外网也可跑）→ 余弦检索 → 工具 `search_regulations`。
3. **和领域的边界**：RAG 只读制度，不改台账；真正开单/关单仍走 CAPA + 审计。
4. **诚实差距**：未接真 embedding API / 向量库（FAISS/pgvector）；未做权限分级文档；rerank / citation 校验可继续加深。

## 路径

- `app/rag/{chunk,embed,store}.py`
- 工具：`search_regulations`（registry + mock eval case）


## 面试官追问（≥5）

**Q1：为什么不用把制度塞进 system prompt？**  
A：制度会更新、会超上下文；RAG 切块检索更可控。本仓 `data/regulations/*.md` → `chunk.py` → hashing embed → `store.search`。

**Q2：没有 embedding API 怎么跑通？**  
A：`embed.py` 用 MD5 hashing bag-of-ngrams + 余弦；确定性，利 CI/Demo。可换真 embedding/FAISS/pgvector。

**Q3：检索结果怎么进 Agent？**  
A：工具 `search_regulations`（只读），出现在 mock eval case；不写台账，开单仍走 CAPA。

**Q4：score 怎么解释给面试官？**  
A：余弦相似度（归一化向量点积）。UI/回复里带 `source`+`score`，可追问 citation。

**Q5：RAG 幻觉与权限？**  
A：本仓诚实差距：无文档级 ACL、无 rerank、无强制 citation 校验。生产要租户文档隔离 + 答案必须引用 chunk id。
