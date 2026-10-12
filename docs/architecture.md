# 架构说明

## 目标

用一个可演示的全栈小项目，讲清楚 **Agent 循环**（观察 → 决策 → 行动 → 再观察），而不是堆框架。

领域选 **EHS 隐患闭环**：查台账、开整改单、查法规摘要——业务语义清晰，面试好讲。

## 组件

```
Browser (Vite/React)
  │  POST /api/chat  →  text/event-stream (SSE)
  │  events: step_start | tool_call | tool_result | final | budget | done
  ▼
FastAPI
  │  agent/loop.py  ← 手写循环（无 LangChain），边跑边 yield
  │  agent/llm.py   ← openai-compatible (default) | mock (opt-in)
  ▼
tools/
  query_hazard_ledger
  create_corrective_ticket
  search_regulations   ← v0 关键词 stub，非向量库
```

非流式 JSON 仍可用：`POST /api/chat/complete`（脚本 / smoke test）。

## Agent 循环（v0）

1. 接收用户消息与可选历史。
2. 调用 LLM（默认真实 OpenAI 兼容接口；`LLM_PROVIDER=mock` 才走规则引擎）得到 `tool_call` 或 `final`。
3. 若 `tool_call`：执行注册表中的工具，把结果追加进上下文，步数 +1；**立刻通过 SSE 推给前端**。
4. 重复直到 `final` 或达到 `MAX_AGENT_STEPS`。
5. 右栏边跑边刷步骤；左栏在 `done` 后写入最终回答。

## 前端

- **左栏**：聊天与快捷提示；流式过程中显示「第 N 步决策中 / 调用工具…」。
- **右栏**：步骤时间线（LIVE 徽章）+ 步数预算条（后续可换成 token 预算）。

## 后续迭代（学习节奏）

| 周次 | 内容 |
|------|------|
| Week1 | 跑通问答 → 工具 → **SSE 可视化**（本仓库 MVP） |
| Week2 | 真向量 RAG、重试/超时、简单评测集 |
| Week3 | 登录权限、一键演示、部署与 README 面试讲法打磨 |

## 为什么先不用框架

框架会变；**循环、工具契约、可观测步骤**不会变。先手写最小循环，面试能讲底层；再接入 LangGraph / 自研编排都会更快。
