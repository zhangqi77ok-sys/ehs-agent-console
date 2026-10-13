# Ch10 课记：会话记忆与上下文压缩

## 面试怎么讲

1. **为什么要压**：多轮 EHS 排查会把制度原文、工具 JSON 灌进 history，超预算会超时/乱答。要「记事」但不能「原文堆」。
2. **分层**：Session 落库保存完整消息；送进 Agent 循环前按 `memory_max_chars` 压缩——旧轮次 mock 摘要，保留最近 K 轮原文。
3. **和 checkpoint 区别**：durable run checkpoint 是单次 run 的工具轨迹；session memory 是跨 turn 对话状态。
4. **诚实差距**：摘要是确定性 mock，不是真 LLM summarize；未做实体记忆（隐患 ID 卡片）与向量长期记忆。

## 路径

- `app/memory/compress.py` · `session_store.py`
- `agent_sessions` 表 · `POST /api/agent/chat` 的 `session_id` / `memory` 字段
