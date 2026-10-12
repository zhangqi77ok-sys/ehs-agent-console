# 第 02 课：给 Agent 加一个新工具 —— `list_open_hazards`

对应提交：[`8e21d20`](https://github.com/zhangqi77ok-sys/ehs-agent-console/commit/8e21d20)  
相关 Issue：[#1 Week1](https://github.com/zhangqi77ok-sys/ehs-agent-console/issues/1) · Day3

---

## 学习目标

学完本课你应该能：

1. 独立完成「**实现函数 → 注册 schema → 写入 dispatch → 提示词点名**」四步，给 Agent 加一个新工具。
2. 说清 **Tool Schema**（给模型看的 JSON）和 **Tool Dispatch**（`run_tool` 真正执行）为什么要分开。
3. 解释：为什么「有哪些待整改隐患」适合用无参工具 `list_open_hazards`，而不是每次都塞参数给 `query_hazard_ledger`。
4. 用真模型提问，在右栏看到 `tool_call: list_open_hazards`，并能对照代码指出调用链。

---

## 改动了哪些文件

| 文件 | 干什么 |
|------|--------|
| `backend/app/tools/hazard_ledger.py` | 新增 `list_open_hazards()`：过滤状态 ∈ {待整改, 整改中}，待整改优先排序 |
| `backend/app/tools/registry.py` | `TOOLS` 注册函数；`TOOL_SCHEMAS` 增加无参 schema；`run_tool` 自动可调 |
| `backend/app/agent/llm.py` | system prompt 点名新工具及选用时机；mock 分支同步（离线演示用） |
| `docs/lessons/02-add-agent-tool.md` | 本课 |
| `docs/lessons/README.md` | 目录索引 |

Agent 循环（`loop.py`）**不用改**：它只消费 `TOOL_SCHEMAS` + `run_tool`，新工具自动进入「决策 → 调用 → 结果」链路。

---

## 核心机制：Schema + Dispatch

```text
用户：「有哪些待整改的隐患」
        │
        ▼
  llm.complete(..., TOOL_SCHEMAS)   ← 模型只看见「有哪些工具、参数长什么样」
        │  返回 tool_call: list_open_hazards {}
        ▼
  run_tool("list_open_hazards", {}) ← registry 按名字找到 Python 函数并执行
        │
        ▼
  结果写回 messages（role=tool）→ 模型再输出最终中文回答
```

### 1. 实现函数（业务逻辑）

```python
def list_open_hazards() -> dict[str, Any]:
    open_statuses = {"待整改", "整改中"}
    items = [deepcopy(h) for h in _HAZARDS if h["status"] in open_statuses]
    items.sort(key=lambda h: (0 if h["status"] == "待整改" else 1, h["id"]))
    return {"count": len(items), "open_statuses": sorted(open_statuses), "items": items}
```

要点：返回 **结构化 dict**（便于模型二次总结），不要只返回一段自然语言字符串。

### 2. Schema（给模型的「说明书」）

```python
{
    "name": "list_open_hazards",
    "description": "列出所有未闭环的隐患（待整改/整改中）。无需参数，适合回答「有哪些待整改/未闭环的隐患」。",
    "parameters": {"type": "object", "properties": {}},
}
```

`description` 写清楚 **何时该用**，比堆砌实现细节更重要——模型靠这段文字选型。

### 3. Dispatch（名字 → 函数）

```python
TOOLS = {
    ...
    "list_open_hazards": list_open_hazards,
}
# run_tool(name, args) → TOOLS[name](**args)
```

漏注册 = 模型能「想」到工具名，但执行时报「未知工具」。面试常追问这点。

### 4. 提示词点名（降低选错工具概率）

在 system prompt 里写：用户问待整改/未闭环时 **优先** `list_open_hazards`。  
Schema 让模型「知道有」，提示词让模型「更愿意选」。

---

## 跟练步骤

1. `git pull`，确认 `registry.py` 里已有 `list_open_hazards`。
2. 重启后端（`--reload` 一般会自动热更；不确定就 Ctrl+C 再 `uvicorn`）。
3. 浏览器提问：**「有哪些待整改的隐患」**。
4. 右栏应出现：
   - `tool_call` · `list_open_hazards` · `arguments: {}`
   - `tool_result` · `count: 2` · 含 `HZ-2026-001`（待整改）与 `HZ-2026-002`（整改中）
5. （加分）自己在 `hazard_ledger.py` 加一条 `status=待整改` 的假数据，再问一次，看 count 是否变 3。**改完记得还原或另开分支。**

脚本冒烟（不启前端）：

```bash
cd backend && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
python -c "import asyncio; from app.agent.loop import run_agent; \
print(asyncio.run(run_agent('有哪些待整改的隐患')))"
```

---

## 思考题

1. **为什么不直接改 `query_hazard_ledger`，而要单独加 `list_open_hazards`？**  
   （提示：无参意图 vs 多过滤条件；schema 清晰度；模型填参错误率。）

2. **如果只改了 Python 函数、忘了写 `TOOL_SCHEMAS`，模型会怎样？**  
   （提示：看不见工具 → 可能胡编答案或乱用旧工具。）

3. **`run_tool` 收到未知工具名时返回 `{"ok": False, ...}` 而不是抛异常——这对 Agent 循环有什么好处？**  
   （提示：错误也能作为 tool 结果喂回模型，让它换策略或向用户说明。）

---

## 和上一课的关系

- [01 · SSE 流式步骤](./01-sse-agent-steps.md)：解决「看得见每一步」。
- **本课**：解决「Agent 能多干一件实事」。  
合在一起：你改工具 → 右栏立刻出现新的 `tool_call` 名字 —— 这就是可观测的 Agent 工程反馈环。
