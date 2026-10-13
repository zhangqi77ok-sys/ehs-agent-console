# 简历项目表述 · EHS 隐患闭环 Agent 控制台

目标岗位：成都 **AI Agent 应用 / Agent 后端**，约 **20–30K**。  
仓库：[ehs-agent-console](https://github.com/zhangqi77ok-sys/ehs-agent-console)（可公开展示）。

---

## 一句话（放项目标题下）

基于 FastAPI 手写 ReAct Agent + SSE 控制台，落地 EHS 隐患/CAPA 闭环；含 SQLAlchemy 持久化、pytest/CI、request_id 可观测与 JWT/API Key 多租户鉴权，并用固定评测集做回归门禁。

---

## 项目描述（简历正文，约 5–7 条）

**EHS 隐患闭环 Agent 控制台**｜个人项目｜Python / FastAPI / React  
面向制造业 EHS 场景，将「查隐患 → 开整改单 → 验收闭环」做成可演示的 Agent 应用，兼顾领域状态机与工程化交付。

- **领域底座**：隐患台账 + CAPA 状态机（待执行→执行中→待验收→关闭/驳回）与 REST；逾期由 deadline 相对 as_of 计算，避免状态双写。
- **手写 Agent Runtime**：自研循环 + 工具注册表对接真实 OpenAI 兼容 LLM（非默认 mock）；SSE 推送步骤/预算，支持超时重试与步数熔断。
- **检索增强**：法规文档分块 + FAISS；网关 embeddings 不可用时本地 TF-IDF 兜底，保证演示可跑。
- **工程化**：SQLAlchemy/Alembic 持久化隐患、整改单与会话；pytest 覆盖状态机/API/ACL（CI 无密钥时 skip LLM eval）；结构化访问日志与 `X-Request-Id`。
- **多租户权限**：`AUTH_MODE=hybrid|strict`，支持 API Key / JWT；令牌身份覆盖客户端伪造的租户/角色头；按车间过滤数据。
- **质量门禁**：`scripts/run_eval.py` 固定用例断言工具调用与关键词，本地有 key 即可回归。

**技术栈**：Python · FastAPI · SQLAlchemy · Alembic · pytest · PyJWT · SSE · Vite/React · FAISS / scikit-learn

---

## 面试 30 秒版（可背）

我在 EHS 场景做了个隐患闭环 Agent 控制台：先把 CAPA 状态机和台账做成真业务 REST，再接手写 Agent 循环接真模型，SSE 看每一步工具调用；后面补了落库迁移、pytest、request_id 日志，以及 JWT/API Key，避免只靠请求头假装多租户。评测脚本用来卡住「会不会乱调工具」。

---

## 量化口径（诚实写法，勿夸大）

| 可写 | 依据 |
|------|------|
| 领域种子 ≥12 条隐患 + CAPA 全链路 | `seed` + 状态机测试 |
| 自动化用例 27+（1 skip 无 key） | `pytest` Eng-02/03 |
| 评测集多 case 全绿（有 LLM key） | `run_eval.py` |
| 公开 GitHub + 中文课记 Eng-01～03 | `docs/lessons/` |

不要写「生产日活 / 大规模集群」等仓库里没有的指标。

---

## 投递时注意

1. 链接放可点击的 GitHub；README 能 5 分钟跑起来。  
2. JD 若写 LangChain/LlamaIndex：强调「先自研 Runtime 讲清机制，框架可替换」。  
3. 若对方偏 Java：补一句「主链路 Python；原 4 年 Java，熟悉后端工程与权限模型」。  
