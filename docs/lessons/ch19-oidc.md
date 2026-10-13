# Ch19 课记：JWKS / OIDC-lite（诚实版）

## 交付

- `AUTH_JWKS_URL`：配置后，**RS256/ES*** Bearer 走 JWKS 验签（`app/auth/jwks.py`）
- 本地 `/auth/token` 仍发 **HS256**（`jwt_secret`），便于 demo / mock
- 优先级：Bearer 头 → 若 alg 非对称且 JWKS 已配 → JWKS；否则 HS256；失败且 JWKS 已配再 fallback

## 诚实声明（面试主动说）

**这不是完整 OIDC IdP**：

| 有 | 没有 |
|----|------|
| JWKS 拉钥 + 验签 | `/authorize` 授权码流 |
| tenant_id / role claim 映射 | refresh token / session |
| 与本地 HS256 共存 | userinfo、PKCE、前端 SSO SDK |

企业入职后通常接 Keycloak / Azure AD / 企微扫码；本仓证明「你知道 JWT 非对称验签与密钥轮换入口」。

## 面试官追问（≥5）

**Q1：为何还保留 HS256？**  
A：离线 demo / pytest 不依赖外网 IdP；生产可关 demo headers 并只信 JWKS。

**Q2：kid 轮换怎么办？**  
A：`PyJWKClient` 缓存 + lifespan；密钥轮换后短 TTL 内拉新 JWKS。

**Q3：缺 tenant_id claim？**  
A：401。多租户身份必须显式进 token，不能靠猜。

**Q4：和 API Key 关系？**  
A：机器调用仍可用 `X-API-Key`；人用 JWT/JWKS。

**Q5：OIDC 完整链路还缺什么？**  
A：授权码、redirect、nonce、refresh、登出——见上表。别把 lite 说成「已接 SSO」。

**Q6：如何本地测 RS256？**  
A：测例起临时 JWKS HTTP server + cryptography 生成 RSA（`test_jwks_ch19.py`）。
