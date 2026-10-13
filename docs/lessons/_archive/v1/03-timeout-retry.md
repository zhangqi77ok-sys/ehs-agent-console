# 第 03 课：超时与重试 —— 让 Agent 调用更可靠

对应提交：[`643607c`](https://github.com/zhangqi77ok-sys/ehs-agent-console/commit/643607c)  
相关 Issue：[#1 Week1](https://github.com/zhangqi77ok-sys/ehs-agent-console/issues/1) · Day4

---

## 学习目标

学完本课你应该能：

1. 说清 **为什么** Agent 调 LLM / 工具必须设超时，以及 **对哪些错误** 才值得重试。
2. 指出本仓库里超时、重试、退避分别写在哪些文件，并能改环境变量调参。
3. 看懂 SSE 的 `note`（重试提示）和 `error`（最终失败）事件，以及工具超时如何变成 `tool_result.ok=false`。
4. 面试时能口述：「超时防止挂死；429/5xx/网络抖动指数退避重试；4xx 一般不重试；工具超时用结构化错误喂回模型」。

---

## 改了什么 / 为什么

| 能力 | 默认 | 环境变量 |
|------|------|----------|
| LLM HTTP 超时 | 60s | `LLM_TIMEOUT_S` |
| LLM 失败后重试次数 | 3（总尝试 = 1+3） | `LLM_MAX_RETRIES` |
| 指数退避基数 | 0.8s（×2^attempt，封顶 20s） | `LLM_RETRY_BACKOFF_S` |
| 单次工具执行超时 | 15s | `TOOL_TIMEOUT_S` |

**为什么要做：**

- 真实网关偶发慢、502、限流（429）。没有超时，uvicorn 工作协程会一直挂着；没有重试，一次抖动就整轮对话失败。
- **只对可恢复错误重试**：`timeout`、传输层错误、`429/500/502/503/504`。像 `401/400` 这类配置/参数错误，重试只会浪费时间和额度。
- 工具（查台账、开单）若将来变成外部 HTTP，也可能卡住；用 `asyncio.wait_for` + `to_thread` 包一层，超时后返回结构化错误，Agent 仍可继续决策或向用户说明。

---

## 文件地图

| 文件 | 干什么 |
|------|--------|
| `backend/app/config.py` | 读入 `LLM_TIMEOUT_S` / `LLM_MAX_RETRIES` / `LLM_RETRY_BACKOFF_S` / `TOOL_TIMEOUT_S` |
| `backend/.env.example` | 文档化上述 knobs（本地复制为 `.env`，**不要提交密钥**） |
| `backend/app/agent/llm.py` | `httpx` 超时；可重试状态码集合；指数退避；抛出 `LLMCallError` |
| `backend/app/tools/registry.py` | `run_tool_async`：线程里跑同步工具 + `TOOL_TIMEOUT_S` |
| `backend/app/agent/loop.py` | 重试时实时 `yield note`；耗尽重试后 `error` + 友好 `final`；工具走 async 包装 |
| `backend/app/main.py` | 捕获 `LLMCallError`；SSE 事件列表含 `note` |
| `frontend/src/App.jsx` / `StepsPanel.jsx` | 展示 `note`（LLM 重试提示） |

调用链（简化）：

```text
stream_agent
  ├─ llm.complete(..., on_retry)
  │     └─ POST /chat/completions
  │           失败且可重试 → on_retry → sleep(backoff) → 再试
  │           仍失败 → LLMCallError → SSE error + final「调用失败：…」
  └─ run_tool_async(name, args)
        └─ wait_for(to_thread(run_tool), TOOL_TIMEOUT_S)
              超时 → {"ok": false, "error": "工具执行超时…"}
```

---

## 跟练步骤

1. `git pull`，确认 `backend/.env.example` 里有 `LLM_TIMEOUT_S` 等四项。
2. 本地 `.env` 补上同样键（可先用默认值）；**不要**把真实 key 提交进 Git。
3. 重启后端：

```powershell
cd ehs-agent-console\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

4. 冒烟（真模型，不启前端）：

```bash
cd backend && source .venv/bin/activate
python -c "import asyncio; from app.agent.loop import run_agent; \
r=asyncio.run(run_agent('有哪些待整改的隐患')); print(r['reply'][:200]); print('steps', len(r['steps']))"
```

5. （推荐）用前端勾选 **「练习：强制超时」** 触发同一路径，详见 [04 · 前端强制超时练习](./04-frontend-timeout-drill.md)。也可把 `LLM_TIMEOUT_S=0.001` 临时改极小；**测完立刻改回 60。**

6. 打开 http://127.0.0.1:5173 ，正常提问，确认 happy path 仍通。

---

## 思考题（Quiz）

1. **为什么 401 Unauthorized 不应该自动重试？**  
   （提示：密钥错了，再试 N 次结果一样，还可能触发风控。）

2. **工具超时返回 `{"ok": false, ...}` 而不是直接抛异常，对 Agent 循环有什么好处？**  
   （提示：错误也能作为 tool 消息喂回模型，让它换工具或向用户解释。）

3. **指数退避为什么比固定 sleep(1) 更好？**  
   （提示：给网关恢复时间；避免雷鸣群（thundering herd）；封顶避免无限拉长。）

4. **`LLM_MAX_RETRIES=3` 时，最坏情况下一次决策最多发起几次 HTTP？**  
   （提示：1 次首次 + 3 次重试 = 4。）

---

## 和前后课的关系

- [01 · SSE](./01-sse-agent-steps.md)：看得见步骤。
- [02 · 新工具](./02-add-agent-tool.md)：Agent 能多干实事。
- **本课**：调用不稳定时不至于整轮翻车，失败也能在 UI 上讲清楚。

下一阶段（Week1 后半 / Week2）：可观测日志、评测集、把超时/重试指标写进 step 预算旁的「健康度」展示。
