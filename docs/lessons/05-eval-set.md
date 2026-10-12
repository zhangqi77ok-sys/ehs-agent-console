# 第 05 课：评测集 —— 给 Agent 加一道「门禁」

对应提交：见本课推送后的 `main` 最新 commit  
相关 Issue：[#1 Week1](https://github.com/zhangqi77ok-sys/ehs-agent-console/issues/1) · Day5  
前置：[02 · 加工具](./02-add-agent-tool.md) · [03 · 超时重试](./03-timeout-retry.md) · [04 · 强制超时练习](./04-frontend-timeout-drill.md)

---

## 学习目标

学完本课你应该能：

1. 说清 **为什么** 作品集 / 面试要讲「评测门禁」，而不是只 demo 几句聊天。
2. 读懂本仓库的轻量评测：`cases.json`（输入 + 期望信号）+ `scripts/run_eval.py`（跑真实 Agent 循环）。
3. 本地 `pull` 后跑通评测，看懂 PASS/FAIL 表；会用 `--only` 单条重跑。
4. 面试口述：「固定用例 → 断言工具名/关键词 → 非零退出码当 CI 门禁；先小而真，再谈框架。」

---

## 改了什么 / 为什么

| 能力 | 说明 |
|------|------|
| 评测用例 | `backend/eval/cases.json`：5 条，覆盖查未闭环、关键词台账、重大隐患、法规检索、开整改单 |
| 跑法 | `backend/scripts/run_eval.py`：调与 UI 相同的 `run_agent()`，真实 LLM（读 `.env`） |
| 判定 | 是否调用了期望工具；最终回答是否含关键词；是否出现「调用失败 / 预算耗尽」 |
| 退出码 | 全部 PASS → `0`；任一 FAIL → 非 `0`（方便以后挂 CI） |

**为什么要做：**

- 控制台能「点着玩」，但面试官常问：**你怎么证明 Agent 没瞎调工具？改 prompt 会不会回归？**
- 答案不是「我手测过」，而是：**有一小撮固定用例 + 可脚本化的 pass/fail**。
- 本课刻意 **不做** 大框架（pytest 插件、LLM-as-judge、并行矩阵）。先把「门禁故事」讲清楚，Week 再往后加。

---

## 文件地图

| 文件 | 干什么 |
|------|--------|
| `backend/eval/cases.json` | 用例：`input` + `expect.tools_*` + `expect.reply_keywords_*` |
| `backend/scripts/run_eval.py` | CLI：加载用例 → `await run_agent` → 打表 → 设退出码 |
| `docs/lessons/05-eval-set.md` | 本课 |
| `docs/lessons/README.md` / 根 `README.md` | 索引与「如何跑评测」入口 |

一条用例长这样（节选）：

```json
{
  "id": "list_open_hazards",
  "name": "列出未闭环隐患",
  "input": "有哪些待整改的隐患？请列出未闭环的。",
  "expect": {
    "tools_required": ["list_open_hazards"],
    "reply_keywords_any": ["HZ-2026-001", "灭火器", "待整改"],
    "must_have_final": true,
    "must_succeed": true
  }
}
```

判定逻辑（简化）：

```text
run_agent(input)
  → steps 里收集 kind=tool_call 的 name
  → reply = final 文本
  → tools_required ⊆ 实际工具？
  → reply 是否命中 keywords_any / keywords_all？
  → 是否像「调用失败：…」或预算熔断？
  → PASS / FAIL
```

---

## 跟练步骤（pull 之后）

### 1. 更新代码并确认配置

```bash
git pull origin main
cd backend
cp -n .env.example .env   # 若还没有 .env
# 编辑 .env：LLM_PROVIDER=openai + OPENAI_API_KEY / BASE_URL / MODEL
# 切勿把 .env 提交进 git
```

### 2. 跑全量评测

```bash
cd backend
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # 若环境是新的
python scripts/run_eval.py -v
```

你会看到类似表格：

```text
id                 | name                 | pass | tools                    | ms   | detail
...
小结: 5/5 PASS, 0 FAIL
```

### 3. 只跑一条（改 prompt / 工具后快速验证）

```bash
python scripts/run_eval.py --only list_open_hazards -v
python scripts/run_eval.py --only create_ticket
```

### 4. 故意搞挂一条（建立直觉）

把 `cases.json` 里某条的 `tools_required` 改成不存在的名字（例如 `list_open_hazards` → `list_open_hazardzzz`），再跑：

- 表里应变 **FAIL**，`detail` 写明「缺少工具 …」
- 进程退出码非 0：`echo $?`

改完记得还原，避免污染自己的门禁。

### 5. 和 UI 对照

同一句 `input` 丢进左侧聊天，看右栏 `tool_call` 是否与评测表里的 `tools` 列一致——**评测跑的就是同一条 `run_agent` 路径**。

---

## 五条用例在考什么

| id | 输入意图 | 主要期望 |
|----|----------|----------|
| `list_open_hazards` | 「待整改 / 未闭环」列表 | 工具 `list_open_hazards` + 回答里出现台账信号 |
| `query_extinguisher` | 关键词查台账 | `query_hazard_ledger` + 灭火器 / HZ-2026-001 |
| `query_major` | 重大隐患 | `query_hazard_ledger` 或 `list_open_hazards` + 重大相关信号 |
| `search_regulations` | 法规 / 闭环制度 | `search_regulations` + 闭环/整改等词 |
| `create_ticket` | 指定编号开单 | `create_corrective_ticket` + 整改单 / CA- / 编号 |

模型偶发选错工具时，这条就会 FAIL——这正是门禁要抓的回归。

---

## 面试可以怎么讲（30 秒）

> 我给 EHS Agent 做了一个**轻量评测门禁**：JSON 里写死 5 个业务问题，脚本走真实 Agent 循环（不是 mock 默认），断言「调了哪个工具 + 最终回答有没有关键信号」。全过退出 0，挂了非 0，以后可以挂 CI。先小而可讲，再演进到更细的断言或 LLM-as-judge。

---

## 思考题

1. 为什么这里用 **关键词 / 工具名** 断言，而不是让另一个大模型打分？各有什么优缺点？
2. `create_ticket` 会改内存台账状态；若把评测并行跑，会出什么问题？怎么隔离？
3. 若要把门禁接到 GitHub Actions，最小还缺哪两步（密钥、命令）？

---

## 下一步

Day5 到此为止。后面 Week1 若继续，再谈预算熔断压力测、更多工具或真实 RAG——**先把这 5 条跑绿**，再加用例，而不是先上框架。
