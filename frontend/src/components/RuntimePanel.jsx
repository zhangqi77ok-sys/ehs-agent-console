import React, { useCallback, useEffect, useState } from "react";

function headers(tenantId, role) {
  return {
    "Content-Type": "application/json",
    "X-Tenant-Id": tenantId,
    "X-Role": role,
    "X-Actor": role,
  };
}

async function jfetch(url, opts) {
  const res = await fetch(url, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

export default function RuntimePanel({ tenantId, role }) {
  const [runs, setRuns] = useState([]);
  const [selected, setSelected] = useState(null);
  const [trace, setTrace] = useState(null);
  const [approvals, setApprovals] = useState([]);
  const [message, setMessage] = useState("查询灭火器隐患");
  const [pauseAfter, setPauseAfter] = useState("1");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [hitl, setHitl] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await jfetch("/api/runs", { headers: headers(tenantId, role) });
      setRuns(data.items || []);
      setHitl(data.hitl_enabled !== false);
      const ap = await jfetch("/api/approvals?status=pending", {
        headers: headers(tenantId, role),
      });
      setApprovals(ap.items || []);
    } catch (e) {
      setError(e.message);
    }
  }, [tenantId, role]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const startRun = async () => {
    setBusy(true);
    setError("");
    try {
      const body = {
        message,
        pause_after_steps: pauseAfter ? Number(pauseAfter) : null,
      };
      const rec = await jfetch("/api/runs", {
        method: "POST",
        headers: headers(tenantId, role),
        body: JSON.stringify(body),
      });
      setSelected(rec);
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const resume = async (runId) => {
    setBusy(true);
    setError("");
    try {
      const rec = await jfetch(`/api/runs/${runId}/resume`, {
        method: "POST",
        headers: headers(tenantId, role),
        body: JSON.stringify({}),
      });
      setSelected(rec);
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const loadTrace = async (runId) => {
    try {
      const t = await jfetch(`/api/runs/${runId}/trace`, {
        headers: headers(tenantId, role),
      });
      setTrace(t);
      const rec = await jfetch(`/api/runs/${runId}`, {
        headers: headers(tenantId, role),
      });
      setSelected(rec);
    } catch (e) {
      setError(e.message);
    }
  };

  const decide = async (approvalId, approve) => {
    setBusy(true);
    setError("");
    try {
      await jfetch(`/api/approvals/${approvalId}/decide`, {
        method: "POST",
        headers: headers(tenantId, role),
        body: JSON.stringify({ approve, note: approve ? "同意" : "驳回" }),
      });
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel">
      <div className="agent-grid">
        <div className="card">
          <h2>Durable Runs</h2>
          <p className="muted small">
            checkpoint / pause / resume · HITL={hitl ? "on" : "off"}
          </p>
          <textarea rows={2} value={message} onChange={(e) => setMessage(e.target.value)} />
          <div className="row gap" style={{ marginTop: 8 }}>
            <label className="small muted">
              pause_after_steps
              <input
                className="narrow"
                value={pauseAfter}
                onChange={(e) => setPauseAfter(e.target.value)}
              />
            </label>
            <button disabled={busy} onClick={startRun}>
              启动 Run
            </button>
            <button className="ghost" disabled={busy} onClick={refresh}>
              刷新
            </button>
          </div>
          {error && <p className="error">{error}</p>}
          <ul className="list" style={{ marginTop: 12 }}>
            {runs.map((r) => (
              <li
                key={r.run_id}
                className={selected?.run_id === r.run_id ? "active" : ""}
                onClick={() => loadTrace(r.run_id)}
              >
                <div className="row between">
                  <code>{r.run_id}</code>
                  <span className="tag">{r.status}</span>
                </div>
                <div className="meta">{r.message}</div>
                {(r.status === "paused" || r.status === "awaiting_approval") && (
                  <button
                    className="ghost"
                    style={{ marginTop: 4 }}
                    disabled={busy || r.status === "awaiting_approval"}
                    onClick={(e) => {
                      e.stopPropagation();
                      resume(r.run_id);
                    }}
                  >
                    {r.status === "awaiting_approval" ? "需先审批" : "Resume"}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>

        <div className="card">
          <h2>详情 / Trace / HITL</h2>
          {selected && (
            <>
              <p className="small">
                <strong>{selected.status}</strong> · budget {selected.budget_used}/
                {selected.budget_max}
              </p>
              <pre className="reply-box">{selected.reply || "(无 reply)"}</pre>
              <h3>Steps</h3>
              <ol className="steps-list">
                {(selected.steps || []).map((s, i) => (
                  <li key={i}>
                    <span className="tag">{s.kind}</span> {s.name || ""}{" "}
                    {s.content || JSON.stringify(s.arguments || s.result || s.note || "").slice(0, 120)}
                  </li>
                ))}
              </ol>
            </>
          )}
          {trace && (
            <>
              <h3>Spans ({trace.span_count}) · {trace.failure_mode}</h3>
              <ol className="steps-list">
                {(trace.spans || []).map((sp) => (
                  <li key={sp.span_id}>
                    <span className="tag">{sp.kind}</span> {sp.name} · {sp.status}
                  </li>
                ))}
              </ol>
            </>
          )}
          <h3>待审批</h3>
          {approvals.length === 0 && <p className="muted small">无 pending</p>}
          <ul className="list">
            {approvals.map((a) => (
              <li key={a.approval_id}>
                <code>{a.tool_name}</code> · {a.run_id}
                <div className="row gap" style={{ marginTop: 4 }}>
                  <button disabled={busy} onClick={() => decide(a.approval_id, true)}>
                    批准
                  </button>
                  <button
                    className="ghost"
                    disabled={busy}
                    onClick={() => decide(a.approval_id, false)}
                  >
                    驳回
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
