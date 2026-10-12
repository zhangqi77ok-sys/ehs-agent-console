# 第 01 课：SSE 流式步骤 —— 让 Agent「边跑边看得见」

对应提交：[`bf19735`](https://github.com/zhangqi77ok-sys/ehs-agent-console/commit/bf19735)  
相关 Issue：[#1 Week1](https://github.com/zhangqi77ok-sys/ehs-agent-console/issues/1)

---

## 学习目标

学完本课你应该能：

1. 说清 **SSE（Server-Sent Events）** 和普通 JSON 响应的差别。
2. 对照代码指出：Agent 循环里哪一行 `yield`、后端怎样写成 `event:` / `data:`、前端怎样解析并刷右栏。
3. 用一句话向面试官解释：**为什么 Agent 产品要流式暴露步骤，而不只返回最终答案**。
4. 本地 `pull` → 重启 → 提问，亲眼看到右栏 **LIVE** 徽章和逐步追加的 `tool_call` / `tool_result`。

---

## 改动了哪些文件（对照 `bf19735`）

| 文件 | 干什么 |
|------|--------|
| `backend/app/agent/loop.py` | 新增 `stream_agent`：循环里每步都 `yield` 事件；`run_agent` 改为消费同一套流再拼成 JSON |
| `backend/app/main.py` | `POST /api/chat` → `StreamingResponse`（`text/event-stream`）；保留 `POST /api/chat/complete` 给脚本 |
| `frontend/src/api/chat.js` | `chatStream`：用 `ReadableStream` 按 `\n\n` 拆 SSE 帧，回调 `onEvent` |
| `frontend/src/App.jsx` | 收到 `tool_call` / `tool_result` / `final` 立刻 `setSteps`；`budget` / `step_start` 更新提示 |
| `frontend/src/components/StepsPanel.jsx` | 流式时显示 **LIVE**；最新一步加高亮 |
| `frontend/src/components/ChatPanel.jsx` | 展示「第 N 步决策中 / 调用工具…」提示 |
| `docs/architecture.md` / `README.md` | 文档同步事件顺序 |

---

## 关键几行在干什么

### 1. Agent 循环：边跑边 `yield`（`loop.py`）

```python
# stream_agent：异步生成器，不是「跑完再返回」
async def stream_agent(message, history=None) -> AsyncIterator[dict]:
    yield {"event": "budget", "data": {"used": 0, "max": budget_max, ...}}

    for i in range(budget_max):
        yield {"event": "step_start", "data": {"index": i + 1, "max": budget_max}}
        decision = await llm.complete(...)   # 等 LLM

        if decision["type"] == "final":
            yield {"event": "final", "data": step}
            yield {"event": "done", "data": payload}
            return

        yield {"event": "tool_call", "data": call_step}   # 先告诉前端「要调谁」
        result = run_tool(name, args)
        yield {"event": "tool_result", "data": result_step}  # 再告诉「结果是什么」
```

要点：

- **一次只调一个工具** → 每轮决策清晰，右栏时间线可读。
- `run_agent` 内部也是 `async for evt in stream_agent(...)`，流式和完整 JSON **共用一套逻辑**，避免两套循环漂移。

### 2. FastAPI：把 `yield` 写成 SSE 帧（`main.py`）

```python
async def event_gen():
    async for evt in stream_agent(body.message, body.history):
        yield (
            f"event: {evt['event']}\n"
            f"data: {json.dumps(evt['data'], ensure_ascii=False)}\n\n"
        )

return StreamingResponse(event_gen(), media_type="text/event-stream", ...)
```

标准 SSE 一帧格式：

```text
event: tool_call
data: {"index":1,"kind":"tool_call","name":"query_hazard_ledger",...}

```

末尾空行（`\n\n`）是帧边界；前端就靠它切片。

### 3. 前端：读流、拆帧、刷 UI（`chat.js` + `App.jsx`）

```javascript
// chat.js：按 \n\n 切帧，解析 event: / data:
const reader = res.body.getReader();
// ... buffer 累积 → 拆出 eventName + JSON → onEvent(eventName, data)
// 收到 done 才 resolve 最终 { reply, steps, budget }
```

```javascript
// App.jsx：事件驱动右栏
chatStream(text, history, (eventName, payload) => {
  if (eventName === "tool_call")  setSteps(prev => [...prev, payload]);
  if (eventName === "tool_result") setSteps(prev => [...prev, payload]);
  if (eventName === "final")       setSteps(prev => [...prev, payload]);
  if (eventName === "budget")      setBudget(payload);
  if (eventName === "step_start")  setStreamingHint(`第 ${payload.index} 步决策中…`);
});
// done 返回后：左栏写入最终 reply
```

事件顺序（正常路径）：

`budget` → `step_start` → `tool_call` → `tool_result` →（可能多轮）→ `final` → `done`

---

## 为什么 Agent 要用流式步骤（面试可讲）

| 非流式「等整轮结束再返回」 | 流式步骤（本课） |
|---------------------------|------------------|
| 用户干等 10–30 秒，不知道卡在 LLM 还是工具 | 立刻看到「正在决策 / 调了哪个工具 / 工具返回了什么」 |
| 出 bug 只能看最终答案猜 | 右栏时间线 = 可观测性（observability） |
| 无法做预算熔断的「过程感」 | `budget` 事件让步数上限可视化 |

一句话：**Agent 的价值不只在最终答案，而在可解释的决策轨迹；SSE 是把轨迹实时推到 UI 的最小工程手段。**

和「打字机式 token 流」的区别：本课流的是 **结构化步骤事件**（tool_call 等），不是把最终回答一个字一个字吐出来。两者可以并存，面试时别混。

---

## 跟练步骤

### 1. 拉代码并重启

```powershell
cd ehs-agent-console
git pull

# 终端 A · 后端
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# 终端 B · 前端
cd ehs-agent-console\frontend
npm run dev
```

打开 <http://127.0.0.1:5173>。确认 `backend/.env` 里 `OPENAI_*` 已填（密钥勿提交）。

### 2. 提问并观察 LIVE

在左栏输入：

> 查一下灭火器相关隐患

预期：

1. 右栏出现 **LIVE** 徽章。
2. 先看到 `tool_call · query_hazard_ledger`（参数里有关键词）。
3. 紧接着 `tool_result`（台账条目）。
4. 再出现 `final`；左栏在结束后才写入完整回复。
5. 底部步数预算条随 `budget` 事件走动。

再试：

> 给 HZ-2026-001 开整改单，措施：更换过期灭火器

对照右栏，口头说出每一步发生了什么。

### 3.（可选）用 curl 看原始 SSE

```bash
curl -N -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"查一下灭火器相关隐患","history":[]}'
```

`-N` 关闭缓冲，才能边收边看。非流式对照：`POST /api/chat/complete`。

---

## 思考题

1. 如果把 `yield tool_call` 挪到 `run_tool` **之后**，用户体验和排障能力会差在哪里？
2. 前端为什么用手动解析 `ReadableStream`，而不是浏览器原生 `EventSource`？（提示：HTTP 方法、自定义 header）
3. `done` 事件里已经带了完整 `steps`，为什么还要在途中逐条 `setSteps`？如果网络极慢，只依赖 `done` 会怎样？

---

## 延伸阅读（仓库内）

- [架构总览](../architecture.md) —— 组件图与周次计划
- [课程目录](./README.md)
- 源码：`backend/app/agent/loop.py`、`backend/app/main.py`、`frontend/src/api/chat.js`
