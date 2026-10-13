# 05 · 评测门禁

## 要解决什么
固定用例跑真实 Agent，挂了非零退出——简历里的「评测门禁」。

```powershell
cd F:\ehs-agent-console\backend
.\.venv\Scripts\Activate.ps1
python scripts\run_eval.py -v
```

用例：`backend/eval/cases.json`

## 验收
- [ ] 本地能跑通（允许偶发模型波动，失败看 detail）
