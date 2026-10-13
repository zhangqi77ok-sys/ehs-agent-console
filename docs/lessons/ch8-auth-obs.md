# Ch8 课记：JWT / API Key + request_id 可观测

## 面试怎么讲多租户鉴权

1. **身份从哪来**：演示环境保留 `X-Tenant-Id` / `X-Role`；对接与联调走 `Authorization: Bearer <JWT>` 或 `X-API-Key`。三者同一套 `get_identity`，优先级 JWT → API Key → 头。
2. **claims 里放什么**：`tenant_id`、`role`、`actor`（及标准 `exp/iat/sub`）。**不要**把权限列表塞成巨型 claims；写权限仍用领域 `domain_can_write(role)`。
3. **租户隔离在哪一层**：鉴权只解决「你是谁」；查库必须带 `tenant_id` 过滤（本仓库 `repo.list_*`），跨租户返回 404 不泄露存在性。
4. **可观测**：每个请求有 `X-Request-Id`（可透传），JSON access log 打 method/path/status/duration，方便和 Agent run / 审计对账。
5. **生产还差什么（诚实）**：密钥轮换、JWKS、Refresh Token、网关侧限流、OpenTelemetry Trace 与 span 对齐——本仓用 HS256 开发密钥，上线必须换 secret 并收紧 `AUTH_REQUIRE_CREDENTIAL`。

## 本仓路径

- `app/auth/jwt_tokens.py` / `api_keys.py` / `deps.py`
- `app/middleware/observability.py`
- `POST /auth/token` · `GET /auth/me`
