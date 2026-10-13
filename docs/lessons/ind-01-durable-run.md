# Ind-01 · 长任务 Run：Checkpoint / 暂停 / 续跑

## 为什么这是「工业级」而不是玩具

面试官问「Agent 跑到一半进程挂了怎么办？」——只答「前端重发」会被追着打。  
本课把 **一次 Agent 执行**提升为有 `run_id` 的耐久对象：每步工具结果后写 checkpoint；可人工/故障暂停；`resume` 从库中状态续跑。

对齐 JD 词：Agent Runtime、长任务状态持久化、checkpoint 恢复（腾讯 Harness / 天鹅到家 Runtime 口径）。

## 做了什么

| 能力 | 位置 |
|------|------|
| 表 `agent_runs` | Alembic `b3e91f0a2c11` |
| 创建 / 续跑 | `app/runs/store.py` + `service.py` |
| 循环挂钩 | `stream_agent(..., resume_state, pause_after_steps, on_checkpoint)` |
| API | `POST /api/runs` · `POST /api/runs/{id}/resume` · `GET /api/runs` |
| 租户隔离 | 非 admin 不能读/续别的 tenant 的 run |

教学开关：`pause_after_steps=1` 模拟「跑完第一步工具后崩溃」。

## 跟练（PowerShell）

```powershell
cd F:\ehs-agent-console
git pull
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# 可选：alembic upgrade head
$env:LLM_PROVIDER="mock"   # 无网也能练断点续跑
uvicorn app.main:app --reload --port 8000
```

```powershell
# 跑一步后暂停
curl -s http://127.0.0.1:8000/api/runs -H "Content-Type: application/json" -H "X-Role: ehs_engineer" -d "{\"message\":\"有哪些未闭环隐患？\",\"pause_after_steps\":1}"

# 记下 run_id 后续跑
curl -s http://127.0.0.1:8000/api/runs/RUN_ID/resume -H "Content-Type: application/json" -H "X-Role: ehs_engineer" -d "{}"
```

`pytest -q` 中 `tests/test_durable_runs.py` 覆盖 pause→resume。

## 面试怎么讲

1. Run 是一等公民，不只是 HTTP 请求。  
2. Checkpoint 落在工具边界（tool_result 后），而不是 token 半截（半截要配合流式缓冲，后续 Ind 可加）。  
3. Resume 会打 `resumed_from_checkpoint` note，方便 Trace/审计（Ind-02 接 span）。

## 验收清单

- [ ] `agent_runs` 表存在（create_all 或 alembic）  
- [ ] `pause_after_steps` 后 status=`paused`，库中有 tool_results  
- [ ] `resume` 后 status=`completed`，steps 含续跑 note  
- [ ] 跨租户 GET run → 403  
- [ ] 课记已 push；`/health` 含 `durable_runs: true`  

下一章 **Ind-02：Span Trace + 回放**。
