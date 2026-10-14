# Day0 · 装环境（让网页能打开）

> 今天目标：**浏览器里看见这个项目的页面。**  
> 做完就停。别往下翻 Day1。

把项目想成两个人在干活：

- **后端** = 厨房（管数据、规矩）  
- **前端** = 点餐屏（你看见的网页）

两边都要开着，网页才有东西吃。

---

## 步骤（Windows 常用 PowerShell）

打开**两个**窗口，别关。

### 窗口 A · 后端

```powershell
cd <你的仓库路径>\ehs-agent-console\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:LLM_PROVIDER="mock"
uvicorn app.main:app --reload --port 8000
```

看到类似 `Uvicorn running on http://127.0.0.1:8000` 就对了。

### 窗口 B · 前端

```powershell
cd <你的仓库路径>\ehs-agent-console\frontend
npm install
npm run dev
```

浏览器打开：**http://127.0.0.1:5173**

你应该看到顶栏有：**Domain 台账 / Agent / Runtime**，还有「租户」「角色」下拉框。

（Mac / Linux 把激活改成 `source .venv/bin/activate`，环境变量用 `LLM_PROVIDER=mock uvicorn ...` 写在同一行即可。）

---

> **今天带走的一句话：**  
> 后端管规矩，前端管画面；两个窗口都开着，才能点。

---

## 卡住了怎么办

- 报错说端口被占用 → 关掉以前开过的终端，或换一台电脑先试。  
- `Activate.ps1` 被禁止 → 用「以管理员打开」或换用 `cmd` 里 `.venv\Scripts\activate.bat`。  
- 页面空白 / 连不上 → 先看窗口 A 还在不在跑；把**完整报错原文**复制出来问人。

---

<details>
<summary>黑话对照（可折叠，今天可不看）</summary>

| 词 | 人话 |
|----|------|
| 后端 / API | 厨房：存数据、检查规矩 |
| 前端 | 你点的网页 |
| venv | 给这个项目专用的 Python 小房间 |
| mock | 假装有 AI，不花钱、结果稳定，方便练习 |

</details>

**做完打勾：□ 我能打开 http://127.0.0.1:5173**  
明天（有空再来）→ [Day1](./Day1-关单必须有证据.md)
