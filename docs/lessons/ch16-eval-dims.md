# Ch16 课记：多维 Eval

## 维度

| 维 | 含义 |
|----|------|
| `tool_correct` | 是否调用期望工具（required / any） |
| `reply_quality` | 回复是否命中关键词（可关闭） |
| `latency_ms` | 单 case 是否 ≤ budget |
| `policy_deny` | 是否按预期出现 `denied`（如 viewer 写） |

## 交付

- `eval/cases.json` 含 `dimensions`；含 **viewer 写拒绝** case
- `scripts/run_eval.py` 打印维表，写 `eval/last_result.json` + `docs/eval-dashboard.md`
- `GET /api/eval/last`
- pytest 断言全维通过

## 面试官追问（≥5）

**Q1：为何不能只看 reply 字符串？**  
A：Agent 可能「说对了但没调工具」；tool_correct 防假成功。

**Q2：policy_deny 维解决什么？**  
A：证明 ACL 在 Agent 路径也生效，不只是 HTTP 403。

**Q3：latency 进 CI 会不会 flaky？**  
A：budget 放宽（15–20s）；mock 无网。真 LLM 另开夜间任务。

**Q4：dashboard 给谁看？**  
A：自己回归；面试可打开 markdown 表。

**Q5：和线上评测差在哪？**  
A：无人工偏好模型、无灰度；是确定性门禁。

**Q6：新 case 怎么加？**  
A：改 `cases.json` 四维配置，跑 `run_eval.py`，看 dashboard。
