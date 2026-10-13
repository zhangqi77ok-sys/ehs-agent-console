# Ch6 课记：确定性 Eval 门禁 + Compose/Postgres

## Eval 为何要 mock 确定性

真 LLM 漂（同一句可能换工具），CI 会抖。  
`LLM_PROVIDER=mock` + `eval/cases.json` 固定输入 → 断言工具名与回复关键词。  
pytest 里 `test_eval_cases_pass_under_mock` **始终跑**；本地也可：

```bash
cd backend && LLM_PROVIDER=mock python scripts/run_eval.py -v
```

面试话术：Eval 测的是 **Agent 轨迹契约**（该调啥工具、答里该出现啥证据），不是文采。

## Compose 形状

`docker compose up --build`：`db` (Postgres 16) + `api` (alembic on start) + `web` (nginx 反代 `/api`)。  
默认本地开发与 pytest 仍用 **SQLite**；生产形状用 `DATABASE_URL=postgresql+psycopg://…`。

## Windows / CI 推送注意

若 GitHub `workflow` OAuth 不足导致 `.github/workflows/ci.yml` 推送被拒：  
**不要把 workflow 文件强推进本次提交**；本机用 GitHub CLI/有 workflow 权限的账号另推。  
业务代码与课记仍可正常 push。

## Demo

1. `pytest -q` 含 eval 绿  
2. （可选）`docker compose up --build` → 浏览器 :5173 走同一套 Domain/Agent/Runtime


## 面试官追问（≥5）

**Q1：cases 断言什么？**  
A：tools_required / reply_keywords / must_succeed。`eval/cases.json`。

**Q2：为何 mock 必须进 CI？**  
A：防回归；真 LLM 抖不能挡合并。

**Q3：Compose 服务？**  
A：postgres + api + nginx（见 `docker-compose.yml`）。

**Q4：迁移何时跑？**  
A：app lifespan alembic upgrade。

**Q5：Eval 失败你怎么查？**  
A：看实际 tools 列表与 reply；对照 mock 路由。
