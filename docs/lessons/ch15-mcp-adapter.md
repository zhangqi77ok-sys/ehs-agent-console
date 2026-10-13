# Ch15 课记：MCP 风格工具适配薄层

## 诚实范围

**不是**完整 MCP Server（无 SSE/stdio 传输、无正式 capability 协商）。  
**是** JD 高频「MCP / Tool Gateway」可指认的 **schema 列表 + invoke** 薄层，底层仍走 `tools/registry` → 领域 API。

## 交付

- `GET /api/mcp/tools` → MCP `tools/list` 形态（`inputSchema`）
- `POST /api/mcp/call` → `{name, arguments}` → `mcp_call_tool` → registry
- 写工具仍受 ACL/`denied` 约束

## JD 关键词怎么映射

| JD 说法 | 本仓 |
|---------|------|
| MCP tools | `/api/mcp/tools` |
| Tool calling gateway | `mcp/adapter.py` + `registry.run_tool` |
| 不旁路业务 | 同 Ch2：只进 `domain_tools` |

## 面试官追问（≥5）

**Q1：为什么不做完整 MCP SSE？**  
A：作品集优先可演示边界；完整协议工期大。薄层足够讲清「工具契约与领域闸门」。

**Q2：和 OpenAI function calling schema 啥关系？**  
A：`TOOL_SCHEMAS` 同源；MCP 适配只是换外壳字段名（`inputSchema`）。

**Q3：外部 Agent 调 /api/mcp/call 安全吗？**  
A：仍要鉴权（JWT/API Key）；viewer 写返回 `denied`。

**Q4：如何扩展新工具？**  
A：registry 注册 + schema；MCP 列表自动暴露。

**Q5：面试官说「你这不是真 MCP」怎么答？**  
A：主动对齐：兼容层 / 非传输完备；给上线路线（加 SSE transport）。

**Q6：多 Agent allowlist 在 MCP 层吗？**  
A：当前 HTTP 适配未挂子 Agent allowlist；Supervisor 路径在 `supervisor.py`。可讲扩展点。
