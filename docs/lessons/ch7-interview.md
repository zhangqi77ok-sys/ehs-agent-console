# Ch7 课记：面试与简历怎么讲这个项目

完整追问稿：[`../interview.md`](../interview.md)  
简历粘贴段：[`../resume-project.md`](../resume-project.md)

## 讲述结构（3 分钟）

1. **痛点**：EHS 假闭环 / 无证据 / 串租户  
2. **Ch1 硬边界**：状态机 + ACL + 审计 + 可点 UI  
3. **Agent**：工具=领域门面；mock 可 Demo；SSE 可观察  
4. **工程**：durable + HITL + trace + eval + Compose  

切忌一上来就说「我接了个大模型」——面试官会当成套壳。

## 作品集检查清单

- [ ] Domain：开单→推进→带证据关闭→审计可见  
- [ ] Agent：同一租户问未闭环 → 能开单且 Domain 同步  
- [ ] Runtime：pause_after_steps → resume；写工具审批  
- [ ] `pytest -q` 全绿；能指到课记章节答追问  

## 薪资锚点话术（成都 20–30k）

强调你能独立交付 **领域服务 + Agent Runtime 最小闭环**，不是只会调 API。  
把 HITL/Eval/多租户讲清楚，比堆模型名更值钱。
