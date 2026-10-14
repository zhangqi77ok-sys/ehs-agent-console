# 面试技术面就绪评分卡（诚实版）

> ⚠️ **先别看这份——跟完 [docs/跟我学](../跟我学/README.md) 再来。**


> 评分只针对**本仓可演示的技术维度**，1–5。  
> **不是 offer 概率**，也不是「保证面试成功」。口语表达、项目与 JD 匹配、对手盘、系统/行为面仍是你的变量。

| 维度 | 分 | 证据 | 说明 |
|------|----|------|------|
| Demo 串戏 | 5 | Domain→Agent→Runtime→Practice 可点通；mock 全链路 | 真 LLM 临场另计 |
| Runtime（循环/SSE/Durable/HITL/Trace） | 5 | Ch2–5 代码+测例 | 非框架黑盒 |
| RAG | 4 | 切块+本地 embedding+score；pgvector 路径 Ch14 | 无生产 ANN 调参/多租户语料隔离 |
| Memory | 4 | Session 压缩 Ch10 | 无长期记忆向量库/跨会话画像 |
| Multi-Agent | 4 | 路由+allowlist+handoff+**并行 fan-out Ch20** | 无 LangGraph 级图编排/共享黑板 |
| Eval | 4 | Mock 门禁+多维+可选 live Ch21 | 无金标集/线上灰度 |
| Auth / 多租户 | 4 | ACL+JWT+API Key+**JWKS lite Ch19** | 无完整 OIDC SSO/细粒度单据权限 |
| Observability | 4 | request_id+summary+/metrics+**OTLP JSON Ch18** | 无全链路 propagator/实连 Tempo |

**加权观感（技术作品集）**：约 **4.2 / 5** —— 够撑 20–30k Agent 应用技术追问；剩余靠你口述与匹配。

## 本仓仍关不掉的残留

1. 完整 IdP（授权码、PKCE、refresh、登出）与企业 SSO 联调  
2. OTel SDK 自动埋点 + W3C TraceContext 跨服务传播 + 实连 collector  
3. 生产级向量检索运维（分片、ANN 调参、租户级语料 ACL）  
4. LangGraph/图编排、共享黑板、大规模并行工作流引擎  
5. 真人口述、白板系统设计、行为面试 —— **仓库无法 closure**

## 使用建议

1. 面前提 Demo 脚本 10 分钟 + oral-15min 各过一遍  
2. Practice Tab 把「不会」清零  
3. 对每个「4 分」维度，主动说清「差在哪、上线怎么补」——比假装 5 分加分  
