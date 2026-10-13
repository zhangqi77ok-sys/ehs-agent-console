# 09 · 把「玩具台账」换成能讲的 EHS 闭环域

## 改了什么

用户反馈业务太假。本课把内存台账做成更接近现场的 **隐患 + 整改单状态机 + 制度摘要**：

- **12 条隐患**：跨车间/类别（消防、电气、机械、危化、动火、有限空间、环保…），含一般/重大、待整改/整改中/待验收/已闭环，并按截止日期计算 **逾期**。
- **整改单 CAPA**：`待执行 → 执行中 → 待验收 → 已关闭`；`create_corrective_ticket` 拒绝已闭环、拒绝重复开单；`advance_corrective_ticket` 做合法迁移，关闭时隐患销号。
- **法规 md**：补上双重预防、危化消防、与台账状态联动的闭环表述；RAG 索引需重建。
- **评测**：增加逾期查询、CA-102 验收关闭等用例。

## 为什么

面试官听「我做了个 Agent」不够，要听你是否懂 **隐患分级、期限、开单、验收销号**。数据和状态机假，故事就假。

## 怎么跟练（Windows PowerShell）

```powershell
cd F:\ehs-agent-console
git pull
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\build_rag_index.py --force
# 终端 A
uvicorn app.main:app --reload --port 8000
# 终端 B
cd ..\frontend
npm install
npm run dev
```

建议话术顺序：

1. 「有哪些重大且已逾期的隐患？」
2. 「给 HZ-2026-001 开整改单…」
3. 「把整改单 CA-102 验收关闭…」
4. 「隐患闭环和双重预防的法规要求是什么？」（看右栏 retrieval heading/score）

评测：

```powershell
cd F:\ehs-agent-console\backend
.\.venv\Scripts\Activate.ps1
python scripts\run_eval.py -v
```

## 思考题

1. 若现场用真实 MES/EHS 库，工具层哪些校验必须下沉到数据库约束？
2. 「逾期」是状态还是计算字段？两种建模对报表和 Agent 提示词各有什么坑？
