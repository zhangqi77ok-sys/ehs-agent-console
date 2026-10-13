import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ACTION_LABELS,
  advanceTicket,
  createTicket,
  legalActions,
  listAudit,
  listHazards,
  listTickets,
} from "../api/domain.js";

const canWrite = (role) => role === "ehs_engineer" || role === "admin";

export default function DomainPanel({ tenantId, role }) {
  const [hazards, setHazards] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [filters, setFilters] = useState({ status: "", level: "", plant: "", keyword: "" });
  const [measures, setMeasures] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [audit, setAudit] = useState([]);
  const [auditError, setAuditError] = useState("");
  const [showAudit, setShowAudit] = useState(true);
  const [evidenceModal, setEvidenceModal] = useState(null); // { ticketId }
  const [evidenceText, setEvidenceText] = useState("");

  const selected = useMemo(
    () => hazards.find((h) => h.id === selectedId) || null,
    [hazards, selectedId]
  );

  const refreshHazards = useCallback(async () => {
    setError("");
    try {
      const data = await listHazards({ tenantId, role, ...filters });
      setHazards(data);
      if (selectedId && !data.some((h) => h.id === selectedId)) {
        setSelectedId(data[0]?.id || null);
      } else if (!selectedId && data.length) {
        setSelectedId(data[0].id);
      }
    } catch (e) {
      setError(e.message);
    }
  }, [tenantId, role, filters, selectedId]);

  const refreshTickets = useCallback(async () => {
    if (!selectedId) {
      setTickets([]);
      return;
    }
    try {
      const data = await listTickets({ tenantId, role, hazardId: selectedId });
      setTickets(data);
    } catch (e) {
      setError(e.message);
    }
  }, [tenantId, role, selectedId]);

  const refreshAudit = useCallback(async () => {
    setAuditError("");
    try {
      const data = await listAudit({ tenantId, role });
      setAudit(data);
    } catch (e) {
      setAudit([]);
      setAuditError(e.message);
    }
  }, [tenantId, role]);

  useEffect(() => {
    refreshHazards();
  }, [tenantId, role, filters.status, filters.level, filters.plant, filters.keyword]);

  useEffect(() => {
    refreshTickets();
  }, [refreshTickets]);

  useEffect(() => {
    refreshAudit();
  }, [refreshAudit]);

  async function onCreateTicket(e) {
    e.preventDefault();
    if (!selectedId || !measures.trim()) return;
    setBusy(true);
    setError("");
    try {
      await createTicket({
        tenantId,
        role,
        hazardId: selectedId,
        measures: measures.trim(),
      });
      setMeasures("");
      await refreshHazards();
      await refreshTickets();
      await refreshAudit();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function doAdvance(ticketId, action, evidenceNote) {
    setBusy(true);
    setError("");
    try {
      await advanceTicket({ tenantId, role, ticketId, action, evidenceNote });
      setEvidenceModal(null);
      setEvidenceText("");
      await refreshHazards();
      await refreshTickets();
      await refreshAudit();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function onActionClick(ticket, action) {
    if (action === "close") {
      setEvidenceModal({ ticketId: ticket.ticket_id });
      setEvidenceText("");
      return;
    }
    doAdvance(ticket.ticket_id, action, null);
  }

  const openTicket = tickets.find((t) => t.status !== "已关闭");

  return (
    <div className="panel">
      {error && <div className="banner error">{error}</div>}

      <div className="grid">
        <section className="card">
          <h2>隐患列表</h2>
          <div className="filters">
            <input
              placeholder="关键词"
              value={filters.keyword}
              onChange={(e) => setFilters((f) => ({ ...f, keyword: e.target.value }))}
            />
            <select
              value={filters.level}
              onChange={(e) => setFilters((f) => ({ ...f, level: e.target.value }))}
            >
              <option value="">级别</option>
              <option value="重大">重大</option>
              <option value="一般">一般</option>
            </select>
            <select
              value={filters.status}
              onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
            >
              <option value="">状态</option>
              <option value="待整改">待整改</option>
              <option value="整改中">整改中</option>
              <option value="待验收">待验收</option>
              <option value="已闭环">已闭环</option>
            </select>
            <select
              value={filters.plant}
              onChange={(e) => setFilters((f) => ({ ...f, plant: e.target.value }))}
            >
              <option value="">车间/厂</option>
              <option value="一厂">一厂</option>
              <option value="二厂">二厂</option>
            </select>
          </div>
          <ul className="list">
            {hazards.map((h) => (
              <li
                key={h.id}
                className={h.id === selectedId ? "active" : ""}
                onClick={() => setSelectedId(h.id)}
              >
                <div className="row">
                  <span className={`tag ${h.level === "重大" ? "danger" : ""}`}>{h.level}</span>
                  <span className="id">{h.id}</span>
                </div>
                <div className="title">{h.title}</div>
                <div className="meta">
                  {h.plant} · {h.category} · {h.status}
                </div>
              </li>
            ))}
            {!hazards.length && <li className="empty">当前租户无隐患</li>}
          </ul>
        </section>

        <section className="card">
          <h2>隐患详情</h2>
          {!selected && <p className="muted">请选择左侧隐患</p>}
          {selected && (
            <>
              <h3>{selected.title}</h3>
              <p>{selected.description}</p>
              <dl className="kv">
                <dt>位置</dt>
                <dd>
                  {selected.plant} / {selected.area}
                </dd>
                <dt>负责人</dt>
                <dd>{selected.owner}</dd>
                <dt>期限</dt>
                <dd>{selected.deadline || "—"}</dd>
                <dt>状态</dt>
                <dd>{selected.status}</dd>
                <dt>风险备注</dt>
                <dd>{selected.risk_note || "—"}</dd>
              </dl>

              {canWrite(role) ? (
                <form className="create-form" onSubmit={onCreateTicket}>
                  <h4>开整改单</h4>
                  {openTicket ? (
                    <p className="muted">已有未关闭整改单 {openTicket.ticket_id}，不可重复开单。</p>
                  ) : selected.status === "已闭环" ? (
                    <p className="muted">隐患已闭环。</p>
                  ) : (
                    <>
                      <textarea
                        rows={3}
                        placeholder="整改措施（必填）"
                        value={measures}
                        onChange={(e) => setMeasures(e.target.value)}
                        required
                      />
                      <button type="submit" disabled={busy || !measures.trim()}>
                        创建整改单
                      </button>
                    </>
                  )}
                </form>
              ) : (
                <p className="muted">当前角色 viewer：只读，无开单按钮。</p>
              )}
            </>
          )}
        </section>

        <section className="card">
          <h2>整改单时间线</h2>
          {!tickets.length && <p className="muted">暂无整改单</p>}
          {tickets.map((t) => (
            <div key={t.ticket_id} className="ticket">
              <div className="row">
                <strong>{t.ticket_id}</strong>
                <span className="tag">{t.status}</span>
              </div>
              <p>{t.measures}</p>
              {t.evidence_note && (
                <p className="evidence">证据：{t.evidence_note}</p>
              )}
              {canWrite(role) && (
                <div className="actions">
                  {legalActions(t.status).map((a) => (
                    <button
                      key={a}
                      type="button"
                      disabled={busy}
                      onClick={() => onActionClick(t, a)}
                    >
                      {ACTION_LABELS[a] || a}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </section>
      </div>

      <section className="card audit">
        <div className="row between">
          <h2>审计</h2>
          <button type="button" className="link" onClick={() => setShowAudit((v) => !v)}>
            {showAudit ? "收起" : "展开"}
          </button>
        </div>
        {showAudit && (
          <>
            {auditError && <p className="banner error">{auditError}</p>}
            {!auditError && (
              <table>
                <thead>
                  <tr>
                    <th>时间</th>
                    <th>角色</th>
                    <th>动作</th>
                    <th>目标</th>
                    <th>结果</th>
                    <th>详情</th>
                  </tr>
                </thead>
                <tbody>
                  {audit.map((a) => (
                    <tr key={a.id} className={a.ok ? "" : "denied"}>
                      <td>{a.ts ? new Date(a.ts).toLocaleString("zh-CN") : "—"}</td>
                      <td>{a.role}</td>
                      <td>{a.action}</td>
                      <td>
                        {a.target_type}:{a.target_id}
                      </td>
                      <td>{a.ok ? "ok" : "denied"}</td>
                      <td>{a.error || JSON.stringify(a.payload)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}
      </section>

      {evidenceModal && (
        <div className="modal-backdrop">
          <div className="modal">
            <h3>关闭整改单 — 填写验收证据</h3>
            <textarea
              rows={4}
              placeholder="非空验收说明（照片编号、仪表读数、复核人等）"
              value={evidenceText}
              onChange={(e) => setEvidenceText(e.target.value)}
              autoFocus
            />
            <div className="actions">
              <button type="button" className="ghost" onClick={() => setEvidenceModal(null)}>
                取消
              </button>
              <button
                type="button"
                disabled={busy || !evidenceText.trim()}
                onClick={() =>
                  doAdvance(evidenceModal.ticketId, "close", evidenceText.trim())
                }
              >
                确认关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
