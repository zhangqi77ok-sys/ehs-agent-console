# 01 · 领域底座（隐患 + 整改单 + REST）

## 这一章要解决什么

Agent 再花哨，台账是玩具，面试官一眼能看穿。第 1 章**先不做聊天**，把 EHS 闭环域做硬：

- 12 条跨车间隐患（级别/类别/期限/逾期计算）
- 整改单状态机：`待执行 → 执行中 → 待验收 → 已关闭`，并与台账联动
- REST 可查、可开、可推进；前端是素表格 + 表单

旧版「先 SSE 再补业务」的课记已进 `_archive/v1/`。

## 关键接口

| 方法 | 路径 | 作用 |
|------|------|------|
| GET | `/api/domain/summary` | 控制台一屏快照 |
| GET | `/api/hazards` | 过滤查询（含 `overdue_only`） |
| GET | `/api/hazards/open` | 未闭环列表 |
| GET | `/api/tickets` | 整改单列表 |
| POST | `/api/tickets` | 开单 |
| POST | `/api/tickets/{id}/advance` | `start` / `submit_verify` / `close` / `reject` |

领域实现：`backend/app/tools/hazard_ledger.py`  
路由：`backend/app/api/domain.py`

## 跟练（Windows PowerShell）

```powershell
cd F:\ehs-agent-console
git pull
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

另开终端：

```powershell
cd F:\ehs-agent-console\frontend
npm install
npm run dev
```

浏览器打开 Vite 地址，建议操作：

1. 看统计卡：未闭环 / 逾期是否合理  
2. 给 `HZ-2026-001` 开整改单  
3. 对 `CA-102` 走 `close`（或先 `start` 一张新单再推进）  
4. 再给已闭环隐患开单 —— 应失败  

curl 自检：

```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/domain/summary
curl "http://127.0.0.1:8000/api/hazards?overdue_only=true"
```

## 验收标准（本章门禁）

- [ ] 台账字段能讲清（车间、类别、级别、期限、逾期）
- [ ] 开单/推进/拒单规则符合状态机
- [ ] 素控制台不靠 Agent 也能走完「查 → 开 → 验」
- [ ] `/health` 显示 `chapter: 1`

## 下一章预告

第 2 章才把手写 Agent 循环接上这些工具；聊天 UI 会回来，但**业务规则以本章 REST 为准**。
