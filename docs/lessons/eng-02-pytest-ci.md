# Eng-02 · pytest + CI 门禁（成都 20–30K 工程补强②）

## 做了什么

给领域状态机与 REST 加上**不依赖 LLM**的自动化测试，并用 GitHub Actions 在每次 push/PR 跑绿。

| 层 | 文件 | 测什么 |
|----|------|--------|
| 状态机 | `backend/tests/test_capa_state_machine.py` | 开单 → start → submit_verify → close；驳回；非法跳转；重复开单 |
| REST/ACL | `backend/tests/test_domain_api.py` | `/health`、隐患列表、viewer 写 403、租户车间过滤、session |
| 租户纯函数 | `backend/tests/test_tenant_auth.py` | `resolve_identity` / 工具白名单 |
| Eval 策略 | `backend/tests/test_eval_skip.py` | **无真实 key 则 skip**；CI 不烧 LLM |
| CI | `.github/workflows/ci.yml` | `pip install` + `pytest -q`，`LLM_PROVIDER=mock` |

真 LLM 评测仍用本地：`python scripts/run_eval.py -v`（需要 `.env` 里的 key）。

## 跟练（PowerShell）

```powershell
cd F:\ehs-agent-console
git pull
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```

看 Actions：仓库 → Actions → **ci** workflow，最新 commit 应为绿色。

有 LLM key 时（可选，不进 CI）：

```powershell
python scripts\run_eval.py -v
```

## 面试怎么讲

- 单元/API 测**确定性业务规则**（状态机、ACL），评测测**模型路径**；门禁分层，避免 CI 被模型抖动拖垮。
- `conftest` 在 import 前用临时 `DATABASE_URL`，避免污染本地 `data/ehs.db`。
- 「缺 key 就 skip」是工程习惯：密钥进 Secrets，不进仓库。

## 验收清单（Definition of Done）

- [ ] `pip install -r requirements.txt` 后本地 `pytest -q` 全绿  
- [ ] 覆盖：CAPA 合法链路 + 至少 1 条非法跳转 + viewer 403 + 租户过滤  
- [ ] `.github/workflows/ci.yml` 存在，push 后 Actions 跑 pytest  
- [ ] 无 `OPENAI_API_KEY` 时 CI/pytest **不失败**（eval skip）  
- [ ] 课记在 `docs/lessons/eng-02-pytest-ci.md`  

通过后进入 **Eng-03：可观测 + 认真版权限**。
