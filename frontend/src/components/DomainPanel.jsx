export default function DomainPanel({
  summary,
  loading,
  error,
  onRefresh,
  onCreate,
  onAdvance,
}) {
  const hazards = summary?.hazards || [];
  const tickets = summary?.tickets || [];

  return (
    <div className="domain">
      <header className="domain-header">
        <div>
          <h1>EHS 隐患闭环 · 第 1 章领域底座</h1>
          <p className="muted">
            先把台账和整改单状态机做真；Agent / SSE 从第 2 章再接。截止日基准：
            {summary?.as_of || "—"}
          </p>
        </div>
        <button type="button" onClick={onRefresh} disabled={loading}>
          {loading ? "刷新中…" : "刷新"}
        </button>
      </header>

      <section className="stats">
        <div className="stat">
          <span className="stat-n">{summary?.hazard_total ?? "—"}</span>
          <span className="stat-l">隐患总数</span>
        </div>
        <div className="stat">
          <span className="stat-n">{summary?.open_count ?? "—"}</span>
          <span className="stat-l">未闭环</span>
        </div>
        <div className="stat warn">
          <span className="stat-n">{summary?.overdue_count ?? "—"}</span>
          <span className="stat-l">逾期</span>
        </div>
        <div className="stat">
          <span className="stat-n">{summary?.ticket_count ?? "—"}</span>
          <span className="stat-l">整改单</span>
        </div>
      </section>

      {error ? <div className="banner error">{error}</div> : null}

      <section className="panel">
        <h2>隐患台账</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>编号</th>
                <th>标题</th>
                <th>车间/区域</th>
                <th>类别</th>
                <th>级别</th>
                <th>状态</th>
                <th>期限</th>
                <th>责任人</th>
              </tr>
            </thead>
            <tbody>
              {hazards.map((h) => (
                <tr key={h.id} className={h.overdue ? "row-overdue" : ""}>
                  <td>
                    <code>{h.id}</code>
                  </td>
                  <td>{h.title}</td>
                  <td>
                    {h.plant}·{h.area}
                  </td>
                  <td>{h.category}</td>
                  <td>{h.level}</td>
                  <td>
                    {h.display_status || h.status}
                    {h.overdue ? " ⚠" : ""}
                  </td>
                  <td>{h.deadline}</td>
                  <td>{h.owner}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel grid-2">
        <div>
          <h2>开整改单</h2>
          <form
            className="form"
            onSubmit={(e) => {
              e.preventDefault();
              const fd = new FormData(e.currentTarget);
              onCreate({
                hazard_id: String(fd.get("hazard_id") || "").trim(),
                measures: String(fd.get("measures") || "").trim(),
                owner: String(fd.get("owner") || "").trim(),
                due_days: Number(fd.get("due_days") || 7),
              });
              e.currentTarget.reset();
            }}
          >
            <label>
              隐患编号
              <input name="hazard_id" placeholder="HZ-2026-001" required />
            </label>
            <label>
              整改措施
              <textarea name="measures" rows={3} required />
            </label>
            <label>
              责任人
              <input name="owner" placeholder="默认用台账责任人" />
            </label>
            <label>
              期限（天）
              <input name="due_days" type="number" defaultValue={7} min={1} />
            </label>
            <button type="submit" disabled={loading}>
              开单
            </button>
          </form>
        </div>
        <div>
          <h2>推进整改单</h2>
          <form
            className="form"
            onSubmit={(e) => {
              e.preventDefault();
              const fd = new FormData(e.currentTarget);
              onAdvance(String(fd.get("ticket_id") || "").trim(), {
                action: String(fd.get("action") || ""),
                evidence_note: String(fd.get("evidence_note") || "").trim(),
              });
              e.currentTarget.reset();
            }}
          >
            <label>
              整改单号
              <input name="ticket_id" placeholder="CA-102" required />
            </label>
            <label>
              动作
              <select name="action" defaultValue="start">
                <option value="start">start 待执行→执行中</option>
                <option value="submit_verify">submit_verify 执行中→待验收</option>
                <option value="close">close 待验收→已关闭（隐患闭环）</option>
                <option value="reject">reject 待验收→执行中</option>
              </select>
            </label>
            <label>
              证据/验收说明
              <textarea name="evidence_note" rows={3} />
            </label>
            <button type="submit" disabled={loading}>
              推进
            </button>
          </form>
        </div>
      </section>

      <section className="panel">
        <h2>整改单列表</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>单号</th>
                <th>隐患</th>
                <th>措施</th>
                <th>责任人</th>
                <th>到期</th>
                <th>状态</th>
                <th>证据</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((t) => (
                <tr key={t.ticket_id}>
                  <td>
                    <code>{t.ticket_id}</code>
                  </td>
                  <td>
                    <code>{t.hazard_id}</code>
                  </td>
                  <td>{t.measures || t.action}</td>
                  <td>{t.owner || t.assignee}</td>
                  <td>{t.due_date}</td>
                  <td>{t.status}</td>
                  <td className="muted">{t.evidence_note || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
