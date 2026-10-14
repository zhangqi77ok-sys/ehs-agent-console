# 如何把过面概率抬上去（可执行版）

> ⚠️ **先别看这份——跟完 [docs/跟我学](../跟我学/README.md) 再来。**


仓库已经把**技术追问空白**压得很低。再涨概率，不靠继续堆章节，靠下面三件事——按顺序做。

## 1. 技术面：把 4 分项讲成「我知道边界」

面试官更吃：**能 demo + 能说清差在哪、上线怎么补**。

| 维度 | 30 秒口径 |
|------|-----------|
| RAG | 本地切块+向量检索已通；生产要 pgvector/ANN 调参和租户语料隔离，Compose 路径已留 |
| Memory | 会话内压缩已测；长期记忆/跨会话画像未做，可接向量记忆表 |
| Multi-Agent | Supervisor 路由+并行 fan-out 真有；不是 LangGraph 图引擎，但协作语义能讲清 |
| Auth | JWT/API Key/JWKS lite；完整 OIDC SSO 是下一迭代 |
| Obs | request_id + metrics + OTLP JSON；实连 Tempo/自动埋点可接 |

**练习**：Practice Tab + `mock-interview.md`，把「不会」清零；每个 4 分项能脱稿说上面那句。

## 2. Demo 面：10 分钟固定剧本（背熟）

按 `docs/demo-script.md` 顺序，不许现场现想：

1. 权限拒绝 + 审计  
2. 无证据关单失败  
3. Agent SSE 查隐患  
4. RAG 查制度  
5. 多 Agent 先查再开单（看双时间线/并行）  
6. HITL 批准写工具  
7. Bearer + Request-Id  
8. 超时或跨租户  

练到：**不看稿也能点**。

## 3. 匹配面：按公司改开场 60 秒

### 鼎桥 / 终端 Agent 类（HITL、Eval、MCP）

> 我做了 EHS 隐患闭环 Agent：手写 Runtime（SSE/断点续跑/HITL/Trace），工具走领域状态机不旁路，带 mock 多维 Eval 和 MCP 风格工具描述层。和贵司 JD 的 Human-on-the-loop、Evaluation Harness、工具链标准化能直接对齐。

### 曙光 / Agent 平台类（Runtime、沙箱、评测、多租户）

> 项目重点在运行平台能力：durable run、span/OTLP、角色工具白名单、多租户隔离、确定性评测门禁。业务用 EHS 验证闭环，平台能力可迁移到贵司 Agent 底座。

### 光学院 / 应用交付类（RAG、Memory、多 Agent、交付）

> 完整交付过 POC→可演示系统：领域台账 + Agent + RAG + 记忆压缩 + Supervisor 多 Agent，Compose/Postgres 可起。强调从需求到评测门禁的工程闭环。

## 诚实预期

| 你的状态 | 技术面大致把握 | 说明 |
|----------|----------------|------|
| Demo 生疏、题库没练 | 偏低 | 先把剧本和 Practice 做完 |
| Demo 顺 + 追问能答边界 | **高** | 已达 20–30k Agent 应用技术门槛 |
| 再加 JD 开场对口 + 行为面准备 | 更高 | 仓库帮不到的部分，靠你 |

**结论**：我对「技术面扛得住成都 20–30k Agent 应用追问」有信心；我对「任意公司必拿 offer」没信心——后者本来就不该由仓库保证。概率提升路径是：**练熟 Demo → 清零追问 → 改开场匹配**，不是无限加章。
