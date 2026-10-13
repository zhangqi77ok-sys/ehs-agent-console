# 面试讲法 · EHS 隐患闭环 Agent 控制台（v2）

面向国内 **3–5 年 Agent 应用 / Python 后端**。只讲仓库里真实有的能力。

仓库：https://github.com/zhangqi77ok-sys/ehs-agent-console

## 30 秒故事

「我按章节重做了一个 EHS 隐患闭环 Agent 控制台：领域侧是隐患台账和 CAPA 状态机；Agent 侧手写 ReAct 循环接真 LLM，SSE 左聊右步骤，带超时重试和步数预算；法规 FAISS RAG（embeddings 失败则 TF-IDF）；会话落库。工程上补了 SQLAlchemy/Alembic、pytest、request_id 结构化日志，以及 JWT/API Key（strict 模式不靠演示头）。业务选 EHS，是因为我有现场背景。」

## 架构

```
领域 REST（台账/CAPA/权限头）
        ↑
手写 loop + tool registry +（可选）session
        ↑ SSE
React：领域页 | Agent 页（租户/角色可切换）
```

## 追问备答

| 追问 | 答法 |
|------|------|
| 为啥不直接上 LangChain？ | 先讲清循环、工具schema、失败与预算；框架以后可换 |
| 逾期是状态还是字段？ | 由 deadline 相对 as_of 计算，避免双写不一致 |
| 评测怎么防 LLM 飘？ | 断言工具名 + 关键词；失败非零退出；可 `--only` |
| 多租户生产怎么做？ | 已有 JWT/API Key + `AUTH_MODE=strict`；演示头仅 hybrid；生产再接 IdP 与行级权限 |
| RAG 为啥 TF-IDF 兜底？ | 网关常无 embeddings；教学要保证可跑 |

## Demo 剧本（5 分钟）

1. 领域页：看逾期统计 → 开单 → 推进  
2. 切 viewer：开单应 403  
3. Agent 页：问重大逾期 → 看 SSE 步骤  
4. 强制超时练习一眼  
5. 问法规闭环 → 指右栏 retrieval  
6. 第二轮指代开单（session）  
7. 提一句 `python scripts/run_eval.py -v`

## 简历粘贴稿

见 [resume-project.md](./resume-project.md)。
