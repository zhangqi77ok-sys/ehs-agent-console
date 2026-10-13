# Ch21 课记：可选 Live LLM Eval

## 交付

- 默认 **mock eval 永远绿**（`pytest` / `scripts/run_eval.py`）
- `LIVE_LLM_EVAL=1` 时跑 `tests/test_live_llm_ch21.py`（需真 `OPENAI_API_KEY` + `LLM_PROVIDER!=mock`）
- 未设置环境变量 → **整文件 skip**，不影响 CI

## 用法

```bash
# 日常 / CI
cd backend && pytest -q

# 可选真模型冒烟（1 条用例）
LIVE_LLM_EVAL=1 LLM_PROVIDER=openai OPENAI_API_KEY=sk-... pytest tests/test_live_llm_ch21.py -v
```

## 面试怎么讲

1. **门禁分层**：确定性 mock 拦回归；live 冒烟抓「提示词/工具 schema 与真模型不兼容」。
2. **为何默认 skip**：真调用贵、不稳、要密钥；作品集 CI 必须可复现。
3. **诚实**：1–2 条 live ≠ 评测集；线上要金标集、抽检、灰度。

## 面试官追问（≥5）

**Q1：mock 绿就能上线吗？**  
A：不能。mock 证明编排/ACL/HITL；live 证明模型契约。

**Q2：live 失败怎么归因？**  
A：先看 tool_call 是否按 schema；再看超时/429；最后才改提示词。

**Q3：为何不用 langchain evaluate？**  
A：本仓自研 harness 够展示维度；标准是「可复现门禁」，不是绑框架。

**Q4：成本怎么控？**  
A：极少用例 + 显式 env 开关；禁止在默认 pytest 打真 API。

**Q5：和 Ch16 多维 Eval？**  
A：Ch16 在 mock 上算 tool/reply/latency/deny；live 只做冒烟连通。
