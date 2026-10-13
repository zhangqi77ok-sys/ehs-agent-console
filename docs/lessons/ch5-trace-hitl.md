# Ch5 课记：Span Trace + 写工具 HITL

## Trace

每次 run 结束后，`replace_spans_from_steps` 把 steps 写成 `agent_spans`（run 根 span + tool/llm/note 子 span）。  
`GET /api/runs/{id}/trace` 返回 spans + `failure_mode`（ok / timeout / tool_denied / …）。  
`GET /api/runs/{id}/replay`：**只读轨迹**，不重新调 LLM——排障与评测对照。

## HITL

配置：`HITL_ENABLED=true`，`HITL_WRITE_TOOLS=create_corrective_ticket,advance_corrective_ticket`。  

写工具被调用前：

1. 落 `tool_call` step  
2. 建 `agent_approvals` pending  
3. run → `awaiting_approval`，checkpoint 带 `pending_tool`  

`POST /api/approvals/{id}/decide`：批准则真正执行领域工具；驳回则写入 denied tool_result；然后自动 resume 让 mock LLM 根据结果 final。

## 为何写工具才闸

读台账风险低；开单/关单一旦执行就进审计与状态机。面试话术：**人在回路守的是不可逆副作用边界，不是每一个 token。**

## Demo

1. Runtime：对 HZ-2026-002 开整改单 → awaiting_approval  
2. 右侧「批准」→ 完成并看到 TK-…  
3. 点 run 看 Trace spans


## 面试官追问（≥5）

**Q1：HITL 插在循环哪一步？**  
A：tool_call 之后、真正 `run_tool_async` 之前。

**Q2：拒绝后 run 状态？**  
A：approval denied；不执行写工具。

**Q3：span 字段？**  
A：kind/name/status/step_index/attrs。`AgentSpan`。

**Q4：replay 为何不调 LLM？**  
A：排障对照；避免副作用与费用。

**Q5：如何扩展到「高风险读」也审批？**  
A：配置 `hitl_write_tools` 集合即可扩。
