# Ch10 课记：会话记忆与上下文压缩

## 面试怎么讲

1. **为什么要压**：多轮 EHS 排查会把制度原文、工具 JSON 灌进 history，超预算会超时/乱答。要「记事」但不能「原文堆」。
2. **分层**：Session 落库保存完整消息；送进 Agent 循环前按 `memory_max_chars` 压缩——旧轮次 mock 摘要，保留最近 K 轮原文。
3. **和 checkpoint 区别**：durable run checkpoint 是单次 run 的工具轨迹；session memory 是跨 turn 对话状态。
4. **诚实差距**：摘要是确定性 mock，不是真 LLM summarize；未做实体记忆（隐患 ID 卡片）与向量长期记忆。

## 路径

- `app/memory/compress.py` · `session_store.py`
- `agent_sessions` 表 · `POST /api/agent/chat` 的 `session_id` / `memory` 字段


## 面试官追问（≥5）

**Q1：Session 和 durable checkpoint 区别？**  
A：Session（`agent_sessions`）跨 turn 对话；checkpoint 是单次 run 工具轨迹暂停续跑（Ch4）。

**Q2：压缩策略？**  
A：超 `memory_max_chars` 时，旧轮次 `mock_summarize`，保留最近 K 轮原文（`compress.py`）。测例 `test_long_history_agent_still_completes` 证明压缩后仍能查台账。

**Q3：摘要用真 LLM 吗？**  
A：默认 mock 确定性摘要，保证 CI；可换成 LLM summarize，但要防摘要丢关键隐患 ID——可加实体卡片记忆。

**Q4：压缩会不会丢开单上下文？**  
A：保留 recent；关键 ID 应在 recent 或摘要里。更深做法：结构化 memory（hazard_id 列表）与原文分离。

**Q5：如何演示给面试官？**  
A：同一 `session_id` 连发多轮长闲聊，看响应 `memory.compressed=true`，再发「查灭火器」仍成功。
