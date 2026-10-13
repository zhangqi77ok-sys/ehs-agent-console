# Ch18 课记：OTLP HTTP JSON 导出（可选）

## 交付

- `app/obs/otlp.py`：内部 span → OTLP `ExportTraceServiceRequest` JSON
- 环境变量 `OTEL_EXPORTER_OTLP_ENDPOINT`（如 `http://localhost:4318`）；**未设置则 no-op**
- `GET /api/runs/{id}/spans/export?format=otlp`：下载 OTLP JSON
- `POST /api/runs/{id}/spans/otlp`：推到 collector（可注入 http_post 测 mock sink）

## 面试怎么讲

1. **Tracing vs Logging**：access log 回答「谁打了哪个 API」；span 回答「这一次 Agent 哪一步超时/拒写」。
2. **为何不做完整 OTel SDK**：作品集要可控依赖；OTLP JSON 够演示「如何对接 collector」，上线再换 protobuf/SDK。
3. **诚实差距**：无自动 instrumentation、无 context propagation 跨服务、无 Tempo/Jaeger 实连（本地测用 mock sink）。

## 面试官追问（≥5）

**Q1：endpoint 空时会发生什么？**  
A：`export_spans_otlp` 返回 `exported=false`，不发网络请求；payload 仍可本地预览。

**Q2：OTLP HTTP 和 gRPC 差在哪？**  
A：本仓用 HTTP JSON（4318 常见路径 `/v1/traces`）；生产常 protobuf 或 gRPC。概念模型相同。

**Q3：traceId 怎么来的？**  
A：lite 实现用 run_id 派生 hex；不是 W3C 全链路传播。面试主动说「上线要接 propagator」。

**Q4：和 Ch13 spans 表什么关系？**  
A：同一 `agent_spans` 数据源；Ch13 下载内部 JSON，Ch18 映射 OTLP 形状。

**Q5：deny/timeout span 的 status？**  
A：映射为 OTLP `STATUS_CODE_ERROR`（code=2），便于在后端标红。

**Q6：如何单测？**  
A：注入 `http_post` mock sink 捕获 url/payload，不依赖真 collector。
