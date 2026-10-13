# Ind-02 · Span Trace + 轨迹回放

## 为什么要做

「黑盒 Agent」过不了 20–30K 追问。需要：**每次工具/回复是一条 span**，失败有 `failure_mode`，并能 **不调 LLM 回放轨迹** 做排障。

## 做了什么

- 表 `agent_spans`（Alembic `c4a22b8d9e01`）
- Run 结束后由 steps **派生** spans（确定性，便于测试）
- `GET /api/runs/{id}/trace` → spans + failure_mode
- `GET /api/runs/{id}/replay` → 录制轨迹回放（不重新打模型）
- `failure_mode`：`ok | paused | timeout | tool_denied | budget_exhausted | llm_or_runtime_error`

## 跟练

```powershell
$env:LLM_PROVIDER="mock"
# 跑完一次
curl -s http://127.0.0.1:8000/api/runs -H "Content-Type: application/json" -H "X-Role: ehs_engineer" -d "{\"message\":\"有哪些未闭环隐患？\"}"
curl -s http://127.0.0.1:8000/api/runs/RUN_ID/trace -H "X-Role: ehs_engineer"
curl -s http://127.0.0.1:8000/api/runs/RUN_ID/replay -H "X-Role: ehs_engineer"
pytest -q tests/test_trace_replay.py
```

## 验收

- [ ] 完整 run 后 trace 含 root `run` span + tool/llm/note  
- [ ] replay 返回 steps/reply 且说明不调 LLM  
- [ ] `/health.agent_trace == true`  
- [ ] pytest 覆盖并通过  

下一章 **Ind-03：写操作 HITL 审批闸**。
