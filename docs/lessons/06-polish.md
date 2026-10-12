# 第 06 课：控制台打磨 —— 让 Demo / 面试更好讲

对应提交：见本文件末尾「对应提交」（推送后回填）  
相关 Issue：[#1 Week1](https://github.com/zhangqi77ok-sys/ehs-agent-console/issues/1) · Day6  
前置：[01 · SSE](./01-sse-agent-steps.md) · [03 · 超时重试](./03-timeout-retry.md) · [05 · 评测门禁](./05-eval-set.md)

---

## 学习目标

学完本课你应该能：

1. 说清 **为什么** 作品集除了「能跑」还要「好演示」：状态可见、失败可解释、预算可感知。
2. 指出本轮 4 处打磨：顶栏健康状态、预算/熔断着色、错误文案可行动、评测门禁露出。
3. 本地 `pull` 后对照 UI，能向面试官口述：「可观测 + 熔断 + 门禁」三条工程信号。
4. 知道下一步读 [面试讲法](../interview.md)（Day7），而不是急着上 Week2。

---

## 改了什么 / 为什么

| 打磨点 | 表现 | 面试话术 |
|--------|------|----------|
| 顶栏状态 | `GET /health` → 后端在线/离线、LLM provider、步数预算、工具数、**评测门禁 · 5 cases** | 「演示前先证明链路活着；门禁不是藏在 README 里」 |
| 预算条 | 接近上限变黄、打满变红并标「已熔断」；显示工具次数 / 重试次数 | 「长任务要有电路熔断，不能无限 ReAct」 |
| 本轮摘要 | 结束后右下角：调用了哪些工具、是否重试、步数占用 | 「一轮跑完能立刻复盘决策路径」 |
| 错误可行动 | Key 缺失 / 超时 / 后端离线 / 预算耗尽 → 附带下一步提示；左栏「本轮异常」横幅 | 「失败要对人友好，不能只 dump 堆栈」 |
| 空态 | 左/右空态写清能做什么、看什么、怎么跑 eval | 「新用户 30 秒内知道怎么玩」 |
| 清空 | 对话标题旁「清空」按钮 | Demo 切场景时干净 |

后端小改：`/health` 多返回 `max_agent_steps`、`tool_count`、`eval_cases`、`eval_cmd`，给顶栏用。

**刻意没做：** 登录、部署、真向量 RAG、CI YAML——留给 Week2/3，避免 Week1 膨胀。

---

## 文件地图

| 文件 | 干什么 |
|------|--------|
| `frontend/src/App.jsx` | 健康状态、友好错误、本轮摘要、把 props 传给左右栏 |
| `frontend/src/components/ChatPanel.jsx` | 空态、清空、错误横幅 |
| `frontend/src/components/StepsPanel.jsx` | 预算着色 / 熔断标签 / 本轮摘要 |
| `frontend/src/styles.css` | chip、error-banner、budget warn/danger |
| `backend/app/main.py` | `/health` 字段扩充 |
| `docs/lessons/06-polish.md` | 本课 |
| `README.md` | Week1 进度与 Day6 说明 |

---

## 跟练步骤（pull 之后）

### 1. 更新并启动

```bash
git pull origin main
# 终端 A
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
# 终端 B
cd frontend && npm run dev
```

打开控制台，看顶栏是否出现：**后端在线 · LLM · openai · 预算 · N 步 · 工具 · 4 · 评测门禁**。

### 2. 正常一轮

点快捷语「查一下灭火器相关隐患」：

- 右栏 LIVE → 出现 tool_call / tool_result / final
- 结束后徽章「本轮完成」+ 摘要里有工具名
- 预算条偏绿/蓝，未熔断

### 3. 感知「接近熔断」（可选）

临时把 `backend/.env` 的 `MAX_AGENT_STEPS=2`，重启后端，发一个可能多步的问题；看预算条变黄/红与「已熔断」文案。测完改回 `8`。

### 4. 错误可行动

- 停掉后端再发一句 → 应提示检查 `:8000`
- 或勾「练习：强制超时」→ 右栏 retry note + 失败横幅带超时提示

### 5. 评测门禁仍在

```bash
cd backend && source .venv/bin/activate && python scripts/run_eval.py -v
```

顶栏只是**露出**门禁；真正门禁仍是脚本退出码。

---

## 思考题

1. 为什么把「评测门禁」做成顶栏 chip，而不是只写在 README？面试时多了哪句？
2. 预算条着色属于产品 UX 还是 Runtime 可观测？两者怎么一起讲？
3. 若 Week2 换成 token 预算，前端哪些字段要改、哪些故事可以复用？

---

## 对应提交

推送后回填 SHA（本轮 Day6 功能提交）。
