# 教学文档（Lessons）

每次功能改动都会在这里追加一篇中文教学文档，方便对照代码自学和面试复盘。

**约定**：任意代码变更 → 同步新增 / 更新一篇 `docs/lessons/NN-主题.md`，并推到远程。

## 目录

| 编号 | 标题 | 对应提交 / 能力 |
|------|------|-----------------|
| [01](./01-sse-agent-steps.md) | SSE 流式步骤 —— 让 Agent「边跑边看得见」 | `bf19735` · `POST /api/chat` SSE + 右栏 LIVE |
| [02](./02-add-agent-tool.md) | 给 Agent 加新工具 —— `list_open_hazards` | `8e21d20` · Week1 Day3 · schema + dispatch |
| [03](./03-timeout-retry.md) | 超时与重试 —— 让 Agent 调用更可靠 | `643607c` · Week1 Day4 · LLM/工具超时 + 退避重试 + SSE note/error |
| [04](./04-frontend-timeout-drill.md) | 前端「强制超时」练习 —— 不用改 .env 也能看见重试 | Week1 Day4 跟练 · `force_timeout` 按请求故障注入 |

## 建议学习顺序

1. 先通读仓库根 [README](../../README.md) 与 [architecture.md](../architecture.md)。
2. 按编号做「跟练步骤」，边改边看右栏。
3. 做完思考题后，对照 Issue [#1](https://github.com/zhangqi77ok-sys/ehs-agent-console/issues/1) 勾 Day 清单。
