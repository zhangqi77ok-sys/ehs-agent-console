# Ind-04 · CI 确定性 Eval 门禁（mock LLM）

## 为什么要做

真模型评测会：烧 token、抖动、CI 无密钥就 skip。面试官问「你们怎么防回归」时，只说「本地跑 eval」不够硬。  
**Ind-04** 把同一条 Agent 环（`run_agent` + `cases.json`）接到 **`LLM_PROVIDER=mock`**：关键词路由确定性，**pytest + CI 双门禁**，无 key 也绿。

分层：

| 层 | 作用 |
|----|------|
| `test_eval_deterministic.py` | 每次 pytest 必跑，mock 全量 cases |
| `scripts/run_eval.py` | CLI / CI 显式一步，exit 0/1 |
| `test_eval_skip.py` | 真 LLM 路径：无 key 仍 skip（不烧钱） |

## 做了什么

1. **`app/agent/llm.py` mock**：补齐逾期 / 重大级别 / 作业票检索 / 开单 / 推进 CAPA 的稳定路由；回复用 `display_status` 带出「逾期」。
2. **`scripts/run_eval.py`**：正式支持 mock；eval 期间 **关闭 HITL**（写工具不等人审，否则 create/advance 会停在 `awaiting_approval`）。
3. **`eval/cases.json`**：开单用例改为无未关单的 `HZ-2026-004`（seed 里 `HZ-2026-001` 已有 CA-103）。
4. **CI**：`.github/workflows/ci.yml` 在 pytest 后加 `LLM_PROVIDER=mock python scripts/run_eval.py`，去掉「eval 仅本地」提醒。

## 跟练（PowerShell）

```powershell
cd F:\ehs-agent-console
git pull
cd backend
.\.venv\Scripts\Activate.ps1
$env:LLM_PROVIDER="mock"
pytest -q
python scripts\run_eval.py -v
```

期望：pytest 全绿；`run_eval` 小结 `8/8 PASS`（或当前 cases 条数全 PASS），进程 exit 0。

有真实 key 时（可选，不进 CI）：

```powershell
$env:LLM_PROVIDER="openai"
# 配好 .env 里的 OPENAI_* 后
python scripts\run_eval.py -v
```

## HITL 与 Eval 的关系（口述要点）

- **产品路径**：Runtime 开跑 → 写工具 → `awaiting_approval` → 人批。
- **评测路径**：同一 `run_agent`，但 **无 `on_hitl` + `hitl_enabled=False`**，写工具直接执行，才能断言最终回复关键词。
- 不是「关掉安全」，而是「门禁测工具选择与业务结果；人审测另开 `test_hitl`」。

## 验收清单

- [ ] `LLM_PROVIDER=mock pytest -q` 绿（含 `test_eval_deterministic`）
- [ ] `LLM_PROVIDER=mock python scripts/run_eval.py` exit 0
- [ ] 无 OpenAI key 时 `test_eval_skip` 仍 skip
- [ ] CI workflow 含 mock eval 步骤（若 push 被 workflow scope 拦，本机补推 ci.yml）

下一章 **Ind-05：Docker Compose + Postgres**。
