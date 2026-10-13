# Ch13 课记：可观测加深

## 交付

- `GET /api/obs/summary`：run 计数、HITL pending、tool deny rate、avg steps、failure_modes
- `GET /metrics`：Prometheus-ish 文本（面试可讲「如何接 Grafana」）
- `GET /api/runs/{id}/spans/export`：可下载 spans JSON
- Runtime UI：摘要条 + failure_mode 标签 + 导出按钮

## Tracing vs Logging（面试必答）

| | Logging | Tracing |
|--|---------|---------|
| 粒度 | 请求/事件一行 | run 内 span 树（tool/llm/note） |
| 用途 | 运维排障、审计旁证 | Agent 步级复盘、评测对照 |
| 本仓 | `middleware/observability.py` + `X-Request-Id` | `agent_spans` + `classify_failure` |

二者互补：access log 回答「谁在什么时候打了哪个 API」；trace 回答「这一次 Agent 为什么开错单 / 为何超时」。

## 面试官追问（≥5）

**Q1：为什么要单独做 /api/obs/summary，而不是只看日志？**  
A：日志是流，摘要是产品化指标（deny rate / HITL 积压）。面试可指 Runtime 顶栏。

**Q2：failure_mode 怎么来的？**  
A：`runs/trace.py` `classify_failure` 扫 steps/status/error，映射 timeout / tool_denied / budget_exhausted 等。

**Q3：导出 spans 给谁用？**  
A：线下复盘、贴到评测 diff、或导入临时分析脚本；不是完整 OTel 导出。

**Q4：和 OpenTelemetry 差在哪？（主动说）**  
A：本仓是轻量 span 表 + JSON 导出；未接 OTLP collector。上线可把同一 span 模型映射到 OTel。

**Q5：deny rate 为何重要？**  
A：反映 ACL/HITL 是否真在拦写工具；突然升高可能是提示词越权或角色配错。

**Q6：avg_steps 飙高说明什么？**  
A：预算浪费或工具抖动；可对照 Eval latency 维。
