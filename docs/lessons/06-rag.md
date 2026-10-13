# 06 · 法规向量 RAG

## 要解决什么
`search_regulations`：切块 + 嵌入 + FAISS；网关无 embeddings 时 `local_tfidf` 兜底。

```powershell
python scripts\build_rag_index.py --force
```

问「隐患闭环和双重预防的要求？」看 `tool_result.retrieval`。

## 验收
- [ ] tool_result 含 backend/heading/score
- [ ] 回答点明条款标题
