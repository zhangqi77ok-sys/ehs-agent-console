# Eval Dashboard（Ch16 多维）

生成时间（UTC）：`2026-10-13T10:19:35.643628+00:00`

**passed=6 failed=0**

| case | tool_correct | reply_quality | latency | policy_deny | overall | ms |
|------|--------------|---------------|---------|-------------|---------|----|
| list_open_hazards | ✅ | ✅ | ✅ | ✅ | PASS | 1.7 |
| query_extinguisher | ✅ | ✅ | ✅ | ✅ | PASS | 1.6 |
| query_major | ✅ | ✅ | ✅ | ✅ | PASS | 1.3 |
| create_ticket | ✅ | ✅ | ✅ | ✅ | PASS | 5.9 |
| search_regulations_fire | ✅ | ✅ | ✅ | ✅ | PASS | 0.5 |
| viewer_write_denied | ✅ | ✅ | ✅ | ✅ | PASS | 0.7 |

重新生成：`cd backend && LLM_PROVIDER=mock python scripts/run_eval.py`

