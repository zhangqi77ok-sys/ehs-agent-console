# 08 · 多租户 / 角色权限雏形

## 要解决什么
用请求头演示租户与角色（非生产 IAM）：

- `X-Tenant-Id`：`default` / `plant_a` / `plant_b` / `hq`
- `X-Role`：`viewer`（只读） / `ehs_engineer` / `admin`

`plant_a` 会过滤到「一号车间」；`viewer` 开单返回 403，Agent 也调不了写工具。

## 跟练
切换角色为只读巡检，尝试开单；切换租户为一号车间，看台账是否变少。

## 验收
- [ ] viewer 无法写
- [ ] plant 租户台账范围正确
