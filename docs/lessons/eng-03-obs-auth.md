# Eng-03 · 可观测 + 认真版权限（成都 20–30K 工程补强③）

## 做了什么

| 能力 | 实现 |
|------|------|
| Request Id | 中间件读写 `X-Request-Id`（无则生成），响应带回 |
| 访问日志 | stdout JSON：`request_id/method/path/status/duration_ms/tenant_id/role/auth` |
| API Key | `X-API-Key` → 环境变量 `API_KEYS=key:tenant:role,...` |
| JWT | `POST /api/auth/token` 换票；`Authorization: Bearer`；HS256 |
| 模式 | `AUTH_MODE=hybrid`（默认，UI 仍可用请求头）/ `strict`（必须 JWT 或 Key） |
| 防伪造 | 有 JWT/Key 时**以令牌为准**，忽略 body/头里的租户角色伪装 |

关键文件：`app/obs/*`、`app/auth/deps.py`、`app/auth/jwt_tokens.py`、`app/auth/api_keys.py`、`app/auth/routes.py`。

## 跟练（PowerShell）

```powershell
cd F:\ehs-agent-console
git pull
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload --port 8000
```

换票与调用：

```powershell
# 用 demo key 换 JWT
curl -s http://127.0.0.1:8000/api/auth/token -H "Content-Type: application/json" -d "{\"api_key\":\"demo-plant-a\"}"

# 带 Key 查隐患（一号车间过滤）
curl -s http://127.0.0.1:8000/api/hazards -H "X-API-Key: demo-plant-a" -D - -o -
# 看响应头 X-Request-Id

# strict 模式：.env 设 AUTH_MODE=strict 后，只带 X-Tenant-Id 会 401
```

预置 demo keys（可在 `.env` 改）：`demo-admin` / `demo-engineer` / `demo-viewer` / `demo-plant-a` / `demo-plant-b`。

## 面试怎么讲

- 可观测：先有 **request_id 贯穿**，再谈 tracing；日志至少能按一次请求拼起来。
- 权限：演示头很好讲课，但简历要写清 **令牌鉴权 + 服务端身份覆盖客户端声明**，否则多租户是假的。
- `hybrid` vs `strict`：本地教学兼容 UI，上线切 strict。

## 验收清单（Definition of Done）

- [ ] 任意 API 响应含 `X-Request-Id`；可回传客户端传入的 id  
- [ ] 访问日志为结构化字段（至少含 request_id、status、duration）  
- [ ] API Key 与 JWT 均可访问领域 API；错误 Key/Token → 401  
- [ ] JWT/Key 身份覆盖伪造的 `X-Tenant-Id` / body.tenant_id  
- [ ] `AUTH_MODE=strict` 时仅靠演示头 → 401  
- [ ] `pytest` 含上述用例且全绿；课记在 `docs/lessons/eng-03-obs-auth.md`  

通过后进入 **Eng-04：成都 20–30K 简历项目描述**。
