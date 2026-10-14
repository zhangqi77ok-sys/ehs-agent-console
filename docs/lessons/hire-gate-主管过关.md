# 课记：主管过关门禁（JWT 续期 / traceparent / 租户 RAG）

## 这章在干啥（人话）

主管招人时会问：「你这套登录过期了怎么办？请求怎么串起来排障？制度检索会不会串厂？」

本轮补的是作品集级答案：

- **自建 JWT 续期 + 登出**（企业登录前的练习，不是 Okta）
- **W3C traceparent**（和 `X-Request-Id` 一起）
- **RAG 按 tenant_id 过滤**
- **pytest 门禁** `tests/test_hire_gate.py`

**不是录用保证。** 文档标题里的「录用标准」= 主管技术过关线。

## 你要会点的

```bash
# 发 token（带 refresh）
curl -s -X POST http://127.0.0.1:8000/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":"demo-plant","role":"ehs_engineer","actor":"me"}'

# 续期
curl -s -X POST http://127.0.0.1:8000/auth/refresh \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token":"<上一步的 refresh_token>"}'

# 登出（作废 refresh）
curl -s -X POST http://127.0.0.1:8000/auth/logout \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token":"<refresh>"}'

# 看 traceparent
curl -sD - -o /dev/null http://127.0.0.1:8000/health \
  -H 'traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01'
```

门禁：

```bash
cd backend && pytest -q tests/test_hire_gate.py
```

## 路径速查

| 能力 | 路径 |
|------|------|
| 发/验/续/登出 | `app/auth/jwt_tokens.py`、`refresh_store.py`、`api/auth.py` |
| traceparent | `app/middleware/observability.py` |
| 租户 RAG | `app/rag/store.py`、`chunk.py`、`tools/domain_tools.py` |
| 门禁测例 | `tests/test_hire_gate.py` |
| 大白话清单 | `docs/主管过关-录用标准.md` |

## 练习怎么练

1. 跑门禁测例，故意改坏一处（比如关单允许空证据）看红灯。  
2. 用 curl 走一遍 token → refresh → logout → 再 refresh 应 401。  
3. 面试口述：「我们先自建 JWT 续期；接公司 IdP 时换成他们的授权码流程，claims 仍带 tenant_id/role。」

## 诚实边界

- refresh 作废是**进程内内存**，重启会丢——作品集够用，生产要落到 Redis/DB。  
- 不是完整 OIDC（没有 authorize / userinfo / 组织同步）。  
- traceparent 是标准头；**真 Tempo** 还要配导出与采样。
