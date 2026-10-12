# 第 08 课：本地向量 RAG —— 把关键词 stub 换成「切块 → 嵌入 → 检索」

对应提交：见本课合并进 `main` 后的 commit（Week2 Day1）  
相关 Issue：[#1](https://github.com/zhangqi77ok-sys/ehs-agent-console/issues/1) · Week2  
前置：[02 · 加工具](./02-add-agent-tool.md) · [05 · 评测门禁](./05-eval-set.md)

---

## 学习目标

学完本课你应该能：

1. 说清 **RAG 最小闭环**：文档切块 → 向量化 → 近邻检索 → 把证据塞进工具结果 → 模型引用作答。
2. 指出本仓库里 **没有用 LangChain**：检索在 `app/rag/`，仍由手写 Agent 循环调 `search_regulations`。
3. 本地 `pull` 后重建索引，问「隐患闭环的法规要求是什么？」，在右栏 `tool_result` 里看到 `retrieval.backend=faiss` 与 `heading`。
4. 面试口述：「网关 embeddings 优先；不通则本地 TF-IDF 兜底，保证跟练不断档。」

---

## 改了什么 / 为什么

| 能力 | 说明 |
|------|------|
| 切块 | `app/rag/chunking.py`：按 `##` 分段，过长再滑动窗口（`RAG_CHUNK_CHARS` / `OVERLAP`） |
| 嵌入 | `app/rag/embeddings.py`：先试 `POST /v1/embeddings`；失败或未配置 → **字符 n-gram TF-IDF**（离线） |
| 索引 | `app/rag/store.py` + `index.py`：**FAISS IndexFlatIP**（向量已 L2 归一化 ≈ 余弦） |
| 工具 | `search_regulations` 返回 `chunks[].score/heading/chunk_id` + `retrieval{backend,embedding,…}` |
| 评测 | `cases.json` 增加作业票用例；`tool_result_keywords_any` 断言 FAISS 证据链 |
| 脚本 | `python scripts/build_rag_index.py [--force]` |

**为什么要做：**

- Week1 关键词 stub 只能演示「会调工具」，讲不清检索质量与可引用性。
- 作品集要能指着右栏说：**证据从哪来、相似度多少、用的哪条嵌入路径**。
- 你当前网关可能 **没有** `/embeddings`（会 404）——所以必须有本地兜底，否则 Demo 挂掉。

---

## 文件地图

```
backend/app/rag/
  chunking.py      # markdown → Chunk
  embeddings.py    # openai | local_tfidf
  store.py         # FAISS
  index.py         # build / lazy load / search
backend/app/tools/rag_stub.py   # search_regulations 入口（模块名保留）
backend/app/data/ehs_regs.md    # 示例法规（可改后 --force 重建）
backend/data/rag/               # index.pkl + meta.json（gitignore，本地生成）
backend/scripts/build_rag_index.py
```

`tool_result` 形状（节选）：

```json
{
  "ok": true,
  "result": {
    "chunks": [
      {"rank": 1, "score": 0.09, "heading": "闭环要求", "chunk_id": "…", "text": "…", "source": "ehs_regs.md"}
    ],
    "retrieval": {
      "backend": "faiss",
      "embedding": "local_tfidf",
      "top_k": 3,
      "query": "隐患闭环的法规要求是什么？"
    }
  }
}
```

---

## 跟练步骤（pull 之后）

### 1. 更新依赖并重建索引

```bash
cd backend
git pull
source .venv/bin/activate
pip install -r requirements.txt
python scripts/build_rag_index.py --force
```

成功时终端会打印 `embedding=local_tfidf` 或 `openai`，以及 `chunks=` / `dim=`。

可选：若你的网关支持 embeddings，在 `.env` 设：

```bash
OPENAI_EMBEDDING_MODEL=text-embedding-3-small   # 按网关实际模型名
RAG_EMBEDDING_PREFER=openai
```

再 `--force` 重建。探测失败会自动回落 TF-IDF，**不必改代码**。

### 2. 起前后端，看右栏证据

```bash
# 终端 A
uvicorn app.main:app --reload --port 8000
# 终端 B
cd ../frontend && npm run dev
```

问一句：**「隐患闭环的法规要求是什么？」**

右栏应出现：

1. `tool_call` → `search_regulations`
2. `tool_result` → `retrieval.backend: faiss`，`chunks[0].heading` 多为「闭环要求」
3. `final` → 中文概括条款（24 小时登记、期限、复查等）

再试：**「高处作业和动火要办什么手续？」** → 应命中「作业票」。

### 3. 跑评测（含 RAG 断言）

```bash
cd backend
python scripts/run_eval.py -v
# 只跑法规：
python scripts/run_eval.py --only search_regulations search_regulations_permit -v
```

`search_regulations*` 会检查 `tool_result` 里是否出现 `"backend": "faiss"` 等信号。

### 4. 改法规再索引

编辑 `backend/app/data/ehs_regs.md`，然后：

```bash
python scripts/build_rag_index.py --force
```

重启或等进程热加载后，新条款才能被检索到（内存单例；`--reload` 下改代码会重置，仅改 md 请 `--force` 或重启）。

---

## 设计取舍（面试可讲）

| 点 | 选择 | 理由 |
|----|------|------|
| 向量库 | FAISS FlatIP | 依赖干净、样例小、余弦直观 |
| 嵌入 | 网关优先 + TF-IDF 兜底 | Demo 不因网关缺 embeddings 挂掉 |
| 框架 | 不用 LangChain/LlamaIndex | 与 Week1「手写循环」叙事一致 |
| 持久化 | `data/rag/*.pkl` gitignore | 可重建；避免提交大文件 |

---

## 思考题

1. 若把 `top_k` 从 3 改成 1，回答更容易漏条款还是更不容易跑题？你怎么在评测里盯住？
2. TF-IDF 与稠密 embedding 在「同义改写」（如「销号」vs「闭环验收」）上谁更弱？如何用一条评测暴露？
3. 右栏已经有 `chunk_id` —— 若要做「点击溯源高亮原文」，前后端还缺哪一步？

---

## 下一步（Week2 后续）

- 多轮会话 / 会话级记忆  
- 更严的引用格式评测（必须出现 heading）  
- 仍不加框架，直到你能徒手画出数据流
