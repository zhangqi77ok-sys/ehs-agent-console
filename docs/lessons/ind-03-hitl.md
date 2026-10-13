# Ind-03 · 写操作 HITL 审批闸 + Runtime UI

## 为什么要做

JD 常写 **human-on-the-loop**：Agent 可以查、可以建议，**真正改台账（开整改单 / 推进状态）必须人点头**。  
否则演示里「一句话开单」在面试官眼里是事故，不是能力。

## 做了什么

### 后端

- 表 `agent_approvals`（Alembic `d5b33c9e0f12`）
- Agent 循环：写工具（默认 `create_corrective_ticket` / `advance_corrective_ticket`）在执行前进入 **`awaiting_approval`**
- `POST /api/approvals/{id}/decide` → 批准后续跑完；拒绝则标记失败/拒绝
- `GET /api/approvals?status=pending`、run 详情带 `pending_approvals`
- `/health.hitl == true`（`HITL_ENABLED`，默认开）

### 前端 Runtime 页（本仓库可演示）

顶栏第三页签 **「Runtime」**：

- 左侧：启动 Run（消息 + 可选 `pause_after_steps`）+ Run 列表（状态色标）
- 右侧：选中 run 的步骤；**待审批**时展示工具名/参数 + 批准/拒绝
- **续跑**（paused）、**Trace**、**Replay** 按钮（覆盖 Ind-01/02）

API 封装：`frontend/src/api/runs.js`（与领域接口同一套 `X-Tenant-Id` / `X-Role`）。

## 跟练（前后端一起看效果）

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:LLM_PROVIDER="mock"
# HITL 默认 True；若关掉可 $env:HITL_ENABLED="false"
uvicorn app.main:app --reload --port 8000
```

另开终端：

```powershell
cd frontend
npm run dev
```

浏览器打开前端 → 顶栏点 **Runtime**：

1. 消息填：`给 HZ-2026-001 开整改单，措施：更换灭火器`
2. **启动 Run** → 状态应变为 **待审批**，右侧出现工具参数
3. 填备注「同意开单」→ **批准** → 状态 **已完成**，可看回复
4. 点 **Trace** / **Replay** 看 span 与轨迹
5. 切到 **领域台账** 刷新，应能看到新整改单

可选 Ind-01：把「跑 N 步后暂停」设为 `1`，启动后点 **续跑**。

验收测试：

```powershell
cd backend
$env:LLM_PROVIDER="mock"
pytest -q tests/test_hitl.py
```

## 验收清单

- [ ] 写工具会停在 `awaiting_approval`，读工具不拦  
- [ ] 工程师可批准；viewer 403  
- [ ] `/health.hitl` 为 true  
- [ ] Runtime 页能走完「启动 → 审批 → 完成」并对照领域台账  
- [ ] `npm run build` 通过  

下一章 **Ind-04：CI 确定性 Eval 门禁**。
