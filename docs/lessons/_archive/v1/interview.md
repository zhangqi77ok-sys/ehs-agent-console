# 面试讲法 · EHS 隐患闭环 Agent 控制台

> 面向国内 **3–5 年 Agent 应用 / Python 后端** 岗位。  
> 只讲本仓库真实能力（手写循环、SSE、工具、超时重试、评测门禁），不吹未做的 Week2。  
> 配套课记：[07 · 面试复盘](./lessons/07-interview.md)

仓库：https://github.com/zhangqi77ok-sys/ehs-agent-console

---

## 1. 30 秒项目故事（开场）

「我做了一个 **EHS 隐患闭环 Agent 控制台**：后端用 **FastAPI 手写 ReAct 风格循环**（不用 LangChain），接真实 OpenAI 兼容网关；前端 Vite/React **左聊天、右步骤**，用 **SSE 边跑边刷** tool_call / tool_result / final。工具覆盖查台账、列未闭环、开整改单、法规摘要 stub。另外做了 **超时+退避重试**、前端强制超时练习，以及 **5 条评测用例脚本当门禁**。业务选 EHS，是因为我有现场域背景，比泛聊天机器人更好讲垂直价值。」

---

## 2. 架构一句话（白板用）

```
用户 → React 控制台
         │ POST /api/chat (SSE)
         ▼
      FastAPI
         │ stream_agent() 手写循环
         │   LLM.complete（超时 / 重试 / note）
         │   TOOLS registry 执行
         │   步数预算熔断
         ▼
      工具：台账 / 开单 / 法规 stub
```

要点：**循环、工具契约、可观测事件、预算** 四件套；框架可后换，这四件面试官更买账。

---

## 3. 手写 Agent 循环 vs 框架（高频）

| 问题 | 建议答法 |
|------|----------|
| 为什么不用 LangChain/LangGraph？ | 先手写最小循环，把 observe→decide→act、工具 schema、步数熔断、SSE 事件模型吃透；框架会变，这套不会。后续接框架是「换编排」，不是「从零学 Agent」。 |
| 和直接 function calling 有什么区别？ | LLM 只负责决策；执行、超时、重试、预算、推送都在 Runtime。把「模型能力」和「工程 Runtime」拆开讲。 |
| 长任务一致性怎么保证？ | ① 步数预算硬熔断 ② 工具结果写回上下文再决策 ③ SSE 暴露每一步便于排障 ④ 评测集防回归。诚实说：尚无持久 checkpoint / 人工确认，Week2 可演进。 |

口述口诀：**模型负责想，Runtime 负责稳，控制台负责看得见，评测集负责不回退。**

---

## 4. 可观测（SSE）怎么讲

- 事件：`budget` → `step_start` → `tool_call` → `tool_result` →（可选 `note` 重试）→ `final` → `done`；失败有 `error` 但仍尽量给 final/done。
- 面试加分句：「不是等整轮结束再吐 JSON，而是 **边跑边推**，和线上排障习惯一致。」
- Demo：右栏 LIVE 徽章、强制超时时出现 `llm_retry` note。

---

## 5. 工具设计（EHS）

| 工具 | 一句话 |
|------|--------|
| `query_hazard_ledger` | 按关键词/状态/级别过滤台账 |
| `list_open_hazards` | 无参列出未闭环（待整改/整改中）——降低「有哪些待整改」的歧义 |
| `create_corrective_ticket` | 针对 hazard_id 开整改单 |
| `search_regulations` | 法规摘要 **关键词 stub**（诚实承认非向量库） |

设计原则可背：

1. **一个工具一个意图**（查 vs 开单 vs 检索分开）
2. **schema 描述写进人话**（模型靠 description 选工具）
3. **失败可结构化返回**（ok / error / timeout），循环能消化
4. **先内存/ stub，边界清晰**，再换 DB / 向量

追问「为什么单独 list_open_hazards？」→ 「query 需要填 status，模型常漏；高频意图用专用工具更稳，评测也更好断言。」

---

## 6. 超时 / 重试 / 强制超时练习

- LLM：`LLM_TIMEOUT_S` + `LLM_MAX_RETRIES` + 指数退避；可重试错误（超时 / 429 / 5xx / 传输）才重试。
- 工具：外层 `TOOL_TIMEOUT_S`，超时写入 result，不拖死整轮。
- **教学注入**：前端勾「练习：强制超时」→ 本请求 `force_timeout`，HTTP 超时约 0.05s，仍走真实网关路径，右栏可见 retry。
- 面试句：「可靠性配置化；故障注入做在请求级，避免改全局 .env 才能演示。」

---

## 7. 评测门禁（Day5）——强烈建议主动讲

- `backend/eval/cases.json`：5 条固定业务输入 + 期望工具名/关键词。
- `scripts/run_eval.py`：调与 UI **同一条** `run_agent()`，真实 LLM；FAIL → 非零退出码。
- 主动说：「我还没上完整 CI，但门禁脚本已经能挂；比『我手测过』硬。」
- 若被问 LLM 非确定性：关键词 + 工具名弱断言；先小而真，再 LLM-as-judge。

---

## 8. Demo 剧本（3–5 分钟）

1. 顶栏：后端在线、LLM、预算、评测 chip（Day6）。
2. 「查灭火器隐患」→ 右栏刷工具。
3. 「给 HZ-2026-001 开整改单…」→ `create_corrective_ticket`。
4. （可选）勾强制超时 → 展示 retry note / 失败横幅。
5. 口头提一句：`python scripts/run_eval.py -v` 当回归门禁。

---

## 9. 可能的 JD 追问 · 短答

**Q：上下文爆了怎么办？**  
A：现在靠步数熔断 + 短历史；下一步会做工具结果摘要、只保留最近 K 轮、关键字段投影。先保证不无限循环。

**Q：怎么防工具乱调 / 写操作风险？**  
A：schema 收窄、开单要 hazard_id、评测断言工具名；生产会加鉴权、幂等键、人工确认写操作。当前是学习向 MVP，写操作在内存。

**Q：RAG 为什么是 stub？**  
A：Week1 目标是 Runtime 与可观测；法规用 markdown 关键词 stub 占位。Week2 换向量检索，工具名可不变，体现「契约稳定、实现可换」。

**Q：和你们线上 Java 服务怎么协作？**  
A：Agent Runtime 适合 Python；台账/权限仍可由 Java 微服务提供，Python 侧 HTTP 调。本项目先内存模拟契约。

**Q：SSE 为什么不用 WebSocket？**  
A：单向步骤流用 SSE 更简单；代理友好；失败回退也清晰。要双向打断再上 WS。

**Q：预算用步数够吗？**  
A：MVP 够讲熔断；生产会叠加 token / 费用预算。前端预算条已按 used/max 抽象，可换单位。

**Q：你最大的工程亮点？**  
A：三件套——**手写循环可讲述**、**SSE 可观测**、**评测脚本可门禁**；外加超时重试与请求级故障注入。

---

## 10. 简历上可写的一行

`EHS Agent 控制台：FastAPI 手写 Agent 循环 + SSE 步骤可视化 + 工具调用 / 超时重试 + 轻量评测门禁（React 控制台）`

---

## 11. 诚实边界（被问到别慌）

| 已做 | 未做（别装做了） |
|------|------------------|
| 真实 LLM、SSE、4 工具、超时重试、强制超时练习、5 条 eval | 登录权限、向量 RAG、持久会话、生产 CI、部署 |

结尾句：「Week1 把 Runtime 与可观测打穿；Week2 再上真 RAG 与工程化。」

---

## 12. 自测清单（面试前一晚）

- [ ] 能不看稿讲 30 秒故事 + 架构一句话  
- [ ] 能当场跑通 UI 一轮工具调用  
- [ ] 能解释 force_timeout 与正常超时的区别  
- [ ] 能跑 `python scripts/run_eval.py -v` 并解释 PASS/FAIL  
- [ ] 能回答「为何手写循环」与「评测如何当门禁」  
