# Ch1 课记：领域台账为什么要先于 Agent

目标读者：面试官追问「你这套 EHS 台账里，状态机 / 权限 / 审计各自解决什么问题？」时能答完整，而不是复述命令。

## 1. 为什么 Ch1 不做 Agent

业务侧真正怕的是：**假整改、无证据闭环、跨厂串数据、事后说不清谁改过状态**。  
Agent 只是调用领域 API 的操作员；若领域本身可被绕过，LLM 再聪明也只是在加速脏数据。  
所以 Ch1 把「隐患 → 整改单 → 验收证据 → 审计」做成可点、可测的硬边界，**Ch1 DoD 未达成前禁止上 Agent / LLM / SSE**。

## 2. 整改单状态机（面试常问）

唯一合法迁移（与 `backend/app/domain/capa.py` 一致）：

| action | from | to | 额外规则 |
|--------|------|-----|----------|
| start | 待执行 | 执行中 | 隐患 → 整改中 |
| submit_verify | 执行中 | 待验收 | 可附证据草稿 |
| close | 待验收 | 已关闭 | **必须**非空 `evidence_note`；隐患 → 已闭环 |
| reject | 待验收 | 执行中 | 隐患回到整改中 |

**为何只要这四态？**

- 「待执行 / 执行中」区分责任是否已开工，避免开单即算完成。
- 「待验收」强制第二人视角（哪怕 Demo 里仍是同一工程师角色），把「做完」和「验收通过」拆开。
- 「已关闭」是终态；从待验收只能 close 或 reject，不能直接跳到别的业务态。

非法迁移返回 **400 + 中文 detail**，状态保持不变，并写 `ticket.denied` 审计——面试里要强调「失败也要可追溯」，不能静默吞掉。

## 3. 为什么关闭必须有验收证据

EHS 场景里「口头说改完了」不够：消防压力表、接地电阻、标识照片等需要留下可复核痕迹。  
实现上 `require_evidence_for_close` 在状态机之前拦截空/空白证据；拒绝时 **同样落审计**（`evidence_provided: false`）。  
成功 close 时审计 payload 带 `evidence_provided: true`，并同步隐患 `closed_at`。

追问：「证据存在哪？」——Ch1 存 `tickets.evidence_note` 文本；附件/对象存储可放后续章，但「无证据不可关」这条规则不能等。

## 4. 角色与租户隔离怎么答

请求头（过渡形态，集中在 `resolve_identity`，禁止路由私读）：

- `X-Tenant-Id`：强制；缺失 400
- `X-Role`：`viewer` / `ehs_engineer` / `admin`；未知回落 viewer

规则：

- **viewer**：读隐患/整改单；**写 403**；**审计 403**
- **ehs_engineer / admin**：可开单、推进；可看本租户审计
- 跨租户：按 `tenant_id` 过滤；拿到别厂 `ticket_id` 也是 **404**（不泄露存在性）+ denied 审计

种子里故意放了 `other-plant` 的隐患，方便顶栏切换租户演示隔离。

## 5. 审计查什么（面试话术）

`audit_events` **只追加**：谁（role/actor）、哪个租户、动作、目标、payload 摘要、ok/denied、错误原因、时间。  
覆盖：开单成功、推进成功、业务拒绝（非法迁移/无证据）、权限拒绝（viewer 写）。  

面试官若问「和操作日志有啥区别？」——审计面向合规追责，字段稳定、不可改删；不是 debug 日志。

## 6. 本地复现（串一条真路径）

```bash
# 后端
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端（另开终端）
cd frontend
npm install
npm run dev
```

浏览器打开 Vite 地址（默认 http://127.0.0.1:5173）：

1. 角色保持 **EHS 工程师**，租户 `demo-plant`
2. 选「灭火器过期未更换」→ 填写措施 → **开整改单**
3. **开始执行** → **提交验收** → **关闭**，弹窗填写非空证据
4. 底部审计应出现 create / advance，且 close 带 evidence 标记
5. 切到 **viewer**：写按钮消失；点审计应看到无权限提示
6. 租户切到 `other-plant`：看不到 demo-plant 的隐患列表

测试：

```bash
cd backend && source .venv/bin/activate && pytest -q
cd ../frontend && npm run build
```

## 7. 与后续章节的边界

- Ch2 起才允许 Agent，且工具**只能**调本领域 API，不能直接改库绕过状态机。
- Postgres/Compose、JWT、HITL、Eval 均不在 Ch1；SQLite 默认可验收。

---

自检：若只能背「跑了哪些命令」而讲不清「为何 close 要证据 / 非法迁移为何写审计」，本课记还没读懂。


## 面试官追问（补强）

**Q1：状态机非法迁移怎么处理？**  
A：纯函数拒绝并返回错误；API/工具层写审计。`domain/capa.py`。

**Q2：evidence 存在哪？**  
A：`tickets.evidence_note`；关闭时强制非空。

**Q3：如何证明非贴皮台账？**  
A：pytest 覆盖迁移/ACL/审计；UI 可点推进。

**Q4：多租户种子数据？**  
A：`seed.py` 按 tenant；测例换 `other-plant`。

**Q5：领域 API 与 Agent 工具关系？**  
A：同一 `repo`；Agent 不得绕过。
