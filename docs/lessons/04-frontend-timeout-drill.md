# 第 04 课：前端「强制超时」练习 —— 不用改 .env 也能看见重试

对应提交：见本仓库 `main` 最新 commit（本课）  
相关：[#1 Week1](https://github.com/zhangqi77ok-sys/ehs-agent-console/issues/1) · Day4 跟练补强  
前置：[03 · 超时与重试](./03-timeout-retry.md)

---

## 学习目标

学完本课你应该能：

1. 说清 **为什么** 要把「强制超时」做成 **按请求的 UI 开关**，而不是每次手改 `LLM_TIMEOUT_S`。
2. 指出请求体里的 `force_timeout` 如何一路传到 `httpx.Timeout`。
3. 在右栏认出 `force_timeout_drill` 与 `llm_retry` 两类 `note`，以及最终的失败 `final`。
4. 面试口述：「教学/联调要用可控故障注入；生产超时仍读配置；开关只影响本轮，不污染全局 .env。」

---

## 改了什么 / 为什么

| 能力 | 行为 |
|------|------|
| 前端勾选「练习：强制超时」 | 本轮 `POST /api/chat` 带 `force_timeout: true` |
| 后端本轮超时 | 仍走真实 OpenAI 兼容路径，但 HTTP 超时改为约 **0.05s**（几乎必触发 `TimeoutException`） |
| 重试可见性 | 退避基数临时用 **0.2s**，几秒内就能看到多次 `llm_retry` |
| 读配置只读展示 | 启动时拉 `/health`，未勾选时显示当前 `llm_timeout_s` / `llm_max_retries` |
| 默认路径 | **不勾选 = 完全不变**；全局 `.env` 的 `LLM_TIMEOUT_S` 不受影响 |

**为什么要做：**

- Day4 课说「把 `LLM_TIMEOUT_S=0.001` 测完改回 60」——容易忘改、也难给别人演示。
- 作品集控制台本意是「左边操作、右边看见」；超时/重试若藏在改配置里，右栏学不到。
- **故障注入要按请求、可开关**：生产逻辑仍用配置；练习开关不进 mock、不改密钥。

---

## 文件地图

| 文件 | 干什么 |
|------|--------|
| `frontend/src/components/ChatPanel.jsx` | 「练习：强制超时」勾选框 + 当前超时只读提示 |
| `frontend/src/api/chat.js` | body 增加 `force_timeout`；`error` 事件不中断流，以便收齐 `final`/`done` |
| `frontend/src/App.jsx` | 把勾选状态传给 `chatStream`；拉 `/health`；展示 retry hint |
| `frontend/src/components/StepsPanel.jsx` | 渲染 `force_timeout_drill` note |
| `frontend/src/styles.css` | `.drill-bar` 练习条样式 |
| `backend/app/main.py` | `ChatRequest.force_timeout`；`/health` 暴露超时/重试只读字段 |
| `backend/app/agent/loop.py` | 透传 `force_timeout`；开练时先发一条 `force_timeout_drill` note |
| `backend/app/agent/llm.py` | 本轮 `timeout_s≈0.05` + 更快退避；mock 下拒绝强制超时并提示改回真实 LLM |

调用链（简化）：

```text
勾选「练习：强制超时」→ POST { force_timeout: true }
  → stream_agent(..., force_timeout=True)
       yield note force_timeout_drill
       → llm.complete(..., force_timeout=True)
            → httpx.Timeout(0.05)  // 仍 POST 真实 /chat/completions
            → TimeoutException → on_retry → note llm_retry → 退避 → 再试
            → 耗尽 → LLMCallError → SSE error + final「调用失败：…」+ done
```

---

## 跟练步骤（UI）

1. `git pull`，重启后端与前端（与平时一样）。
2. 打开 http://127.0.0.1:5173 。
3. 确认左下角练习条显示类似：`正常超时 60s · 重试 3 次`（数字来自 `/health`）。
4. **勾选「练习：强制超时」**（条会变黄）。
5. 随便发一句，例如点提示「查一下灭火器相关隐患」或输入「你好」。
6. 看右栏，应依次出现：
   - `note · force_timeout_drill`（说明本轮是练习）
   - 若干 `note · llm_retry`（`timeout after 0.05s（练习：强制超时）`）
   - `final`：`调用失败：LLM 调用失败（已重试 N 次）：…`
7. **取消勾选**，再发同一句 → 应恢复正常工具调用 / 最终回答（证明开关只影响本轮）。

> 需要真实 LLM（`LLM_PROVIDER=openai` + 有效密钥）。若仍是 mock，会直接提示「强制超时练习需要真实 LLM」。

---

## 思考题（Quiz）

1. **为什么强制超时仍要打真实网关，而不是直接在后端 `raise TimeoutError`？**  
   （提示：练习的是整条 HTTP 超时 → 重试 → SSE note 路径，不是 mock 一段假文案。）

2. **若把 `force_timeout` 做成改全局 `settings.llm_timeout_s`，会有什么坑？**  
   （提示：并发请求互相踩；忘记改回；热重载/多 worker 状态不一致。）

3. **前端以前在 `error` 事件上直接 `throw`，对「看右栏重试」有什么坏处？本课为何改成继续读到 `done`？**  
   （提示：loop 在 `error` 之后还会发 `final`/`done`；中途抛出会丢掉失败文案进气泡的路径。）

---

## 和前后课的关系

- [03 · 超时与重试](./03-timeout-retry.md)：机制本身（配置、退避、可重试状态码）。
- **本课**：把机制变成 **可点击的练习**，方便自学和演示。
- 下一阶段：评测集、可观测指标，把超时/重试次数写进健康度展示。
