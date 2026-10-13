import { useCallback, useEffect, useState } from "react";
import {
  decideApproval,
  getReplay,
  getRun,
  getTrace,
  listRuns,
  resumeRun,
  startRun,
} from "../api/runs.js";

const STATUS_LABEL = {
  pending: "待执行",
  running: "运行中",
  paused: "已暂停",
  awaiting_approval: "待审批",
  completed: "已完成",
  failed: "失败",
};

function statusClass(s) {
  if (s === "completed") return "ok";
  if (s === "failed") return "fail";
  if (s === "awaiting_approval") return "warn";
  if (s === "paused") return "paused";
  if (s === "running") return "run";
  return "";
}

export default function RuntimePanel({ identity }) {
  const [runs, setRuns] = useState([]);
  const [hitlEnabled, setHitlEnabled] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [selected, setSelected] = useState(null);
  const [message, setMessage] = useState(
    "给 HZ-2026-001 开整改单，措施：更换灭火器"
  );
  const [pauseAfter, setPauseAfter] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [trace, setTrace] = useState(null);
  const [replay, setReplay] = useState(null);
  const [side, setSide] = useState("steps"); // steps | trace | replay

  const refreshList = useCallback(async () => {
    setError("");
    try {
      const data = await listRuns(identity);
      setRuns(data.items || []);
      setHitlEnabled(data.hitl_enabled);
    } catch (e) {
      setError(e.message || String(e));
    }
  }, [identity.tenant_id, identity.role]);

  const loadSelected = useCallback(
    async (runId) => {
      if (!runId) {
        setSelected(null);
        return;
      }
      setError("");
      try {
        const rec = await getRun(runId, identity);
        setSelected(rec);
        setSelectedId(runId);
      } catch (e) {
        setError(e.message || String(e));
      }
    },
    [identity.tenant_id, identity.role]
  );

  useEffect(() => {
    refreshList();
  }, [refreshList]);

  useEffect(() => {
    if (selectedId) loadSelected(selectedId);
  }, [selectedId, identity.tenant_id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function onStart(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setTrace(null);
    setReplay(null);
    setSide("steps");
    try {
      const payload = { message: message.trim() };
      const n = parseInt(pauseAfter, 10);
      if (!Number.isNaN(n) && n >= 1) payload.pause_after_steps = n;
      const rec = await startRun(payload, identity);
      await refreshList();
      setSelected(rec);
      setSelectedId(rec.run_id);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  async function onResume() {
    if (!selectedId) return;
    setLoading(true);
    setError("");
    try {
      const rec = await resumeRun(selectedId, {}, identity);
      await refreshList();
      setSelected(rec);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  async function onDecide(approve) {
    const pending = selected?.pending_approvals || [];
    if (!pending.length) return;
    setLoading(true);
    setError("");
    try {
      const res = await decideApproval(
        pending[0].approval_id,
        { approve, note },
        identity
      );
      setNote("");
      await refreshList();
      const run = res.run || (await getRun(selectedId, identity));
      setSelected(run);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  async function onTrace() {
    if (!selectedId) return;
    setLoading(true);
    setError("");
    try {
      const t = await getTrace(selectedId, identity);
      setTrace(t);
      setSide("trace");
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  async function onReplay() {
    if (!selectedId) return;
    setLoading(true);
    setError("");
    try {
      const r = await getReplay(selectedId, identity);
      setReplay(r);
      setSide("replay");
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  const pending = selected?.pending_approvals || [];
  const steps = selected?.steps || [];

  return (
    <div className="runtime">
      <header className="domain-header">
        <div>
          <h1>Runtime · 长任务 / Trace / HITL</h1>
          <p className="muted">
            Ind-01 断点续跑 · Ind-02 Trace/回放 · Ind-03 写工具人工审批
            {hitlEnabled === true ? " · HITL 已开启" : hitlEnabled === false ? " · HITL 关闭" : ""}
          </p>
        </div>
        <button type="button" onClick={refreshList} disabled={loading}>
          {loading ? "处理中…" : "刷新列表"}
        </button>
      </header>

      {error ? <div className="banner error">{error}</div> : null}

      <div className="runtime-layout">
        <aside className="runtime-left">
          <section className="panel">
            <h2>启动 Run</h2>
            <form className="form" onSubmit={onStart}>
              <label>
                消息
                <textarea
                  rows={3}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  required
                />
              </label>
              <label>
                可选：跑 N 步后暂停（Ind-01）
                <input
                  type="number"
                  min={1}
                  placeholder="留空则不停"
                  value={pauseAfter}
                  onChange={(e) => setPauseAfter(e.target.value)}
                />
              </label>
              <button type="submit" disabled={loading || !message.trim()}>
                启动 Run
              </button>
            </form>
            <p className="muted tip">
              HITL 演示：用写操作消息（如「给 HZ-2026-001 开整改单…」），状态会变成「待审批」。
            </p>
          </section>

          <section className="panel">
            <h2>Run 列表（{runs.length}）</h2>
            <div className="run-list">
              {runs.length === 0 ? (
                <p className="muted">暂无 run，先启动一条。</p>
              ) : (
                runs.map((r) => (
                  <button
                    type="button"
                    key={r.run_id}
                    className={`run-item${selectedId === r.run_id ? " on" : ""}`}
                    onClick={() => {
                      setSelectedId(r.run_id);
                      setTrace(null);
                      setReplay(null);
                      setSide("steps");
                    }}
                  >
                    <span className={`status-chip ${statusClass(r.status)}`}>
                      {STATUS_LABEL[r.status] || r.status}
                    </span>
                    <span className="run-id">
                      <code>{r.run_id}</code>
                    </span>
                    <span className="run-msg muted">{r.message}</span>
                  </button>
                ))
              )}
            </div>
          </section>
        </aside>

        <main className="runtime-right">
          {!selected ? (
            <section className="panel">
              <p className="muted">选择左侧 run，或启动新 run 查看步骤 / Trace / 审批。</p>
            </section>
          ) : (
            <>
              <section className="panel">
                <div className="runtime-detail-head">
                  <div>
                    <h2>
                      <code>{selected.run_id}</code>{" "}
                      <span className={`status-chip ${statusClass(selected.status)}`}>
                        {STATUS_LABEL[selected.status] || selected.status}
                      </span>
                    </h2>
                    <p className="muted">{selected.message}</p>
                    {selected.reply ? (
                      <p className="reply-preview">回复：{selected.reply}</p>
                    ) : null}
                    {selected.error ? (
                      <p className="banner error" style={{ marginTop: "0.5rem" }}>
                        {selected.error}
                      </p>
                    ) : null}
                  </div>
                  <div className="runtime-actions">
                    {selected.status === "paused" ? (
                      <button type="button" onClick={onResume} disabled={loading}>
                        续跑 Resume
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => setSide("steps")}
                      disabled={loading}
                    >
                      步骤
                    </button>
                    <button type="button" className="btn-secondary" onClick={onTrace} disabled={loading}>
                      Trace
                    </button>
                    <button type="button" className="btn-secondary" onClick={onReplay} disabled={loading}>
                      Replay
                    </button>
                  </div>
                </div>

                {selected.status === "awaiting_approval" && pending.length > 0 ? (
                  <div className="hitl-box">
                    <h3>待审批写工具</h3>
                    {pending.map((ap) => (
                      <div key={ap.approval_id} className="hitl-item">
                        <p>
                          <strong>{ap.tool_name}</strong>{" "}
                          <code className="muted">{ap.approval_id}</code>
                        </p>
                        <pre>{JSON.stringify(ap.arguments || {}, null, 2)}</pre>
                      </div>
                    ))}
                    <label>
                      审批备注（可选）
                      <input
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder="例如：同意开单"
                      />
                    </label>
                    <div className="hitl-btns">
                      <button type="button" onClick={() => onDecide(true)} disabled={loading}>
                        批准 Approve
                      </button>
                      <button
                        type="button"
                        className="btn-danger"
                        onClick={() => onDecide(false)}
                        disabled={loading}
                      >
                        拒绝 Reject
                      </button>
                    </div>
                  </div>
                ) : null}
              </section>

              <section className="panel">
                {side === "steps" ? (
                  <>
                    <h2>步骤（{steps.length}）</h2>
                    <div className="steps">
                      {steps.length === 0 ? (
                        <p className="muted">尚无步骤。</p>
                      ) : (
                        steps.map((s, i) => (
                          <div className="step" key={i}>
                            <span className={`kind ${s.kind || ""}`}>
                              #{s.index ?? i} {s.kind}
                              {s.name ? ` · ${s.name}` : ""}
                              {s.note ? ` · ${s.note}` : ""}
                            </span>
                            <pre>
                              {s.kind === "tool_call" &&
                                JSON.stringify(s.arguments ?? {}, null, 2)}
                              {s.kind === "tool_result" &&
                                JSON.stringify(s.result ?? {}, null, 2)}
                              {s.kind === "final" && (s.content || "")}
                              {s.kind === "note" && JSON.stringify(s, null, 2)}
                              {!["tool_call", "tool_result", "final", "note"].includes(s.kind) &&
                                JSON.stringify(s, null, 2)}
                            </pre>
                          </div>
                        ))
                      )}
                    </div>
                  </>
                ) : null}

                {side === "trace" ? (
                  <>
                    <h2>
                      Trace · failure_mode={" "}
                      <code>{trace?.failure_mode || "—"}</code>（{trace?.span_count ?? 0} spans）
                    </h2>
                    <div className="steps">
                      {(trace?.spans || []).map((sp, i) => (
                        <div className="step" key={sp.span_id || i}>
                          <span className="kind">
                            {sp.kind || sp.span_kind || "span"} · {sp.name || sp.span_name || ""}
                          </span>
                          <pre>{JSON.stringify(sp, null, 2)}</pre>
                        </div>
                      ))}
                      {!trace?.spans?.length ? <p className="muted">无 span。</p> : null}
                    </div>
                  </>
                ) : null}

                {side === "replay" ? (
                  <>
                    <h2>Replay · {replay?.mode || "recorded_trajectory"}</h2>
                    <p className="muted">{replay?.note}</p>
                    <div className="steps">
                      {(replay?.steps || []).map((s, i) => (
                        <div className="step" key={i}>
                          <span className={`kind ${s.kind || ""}`}>
                            #{s.index ?? i} {s.kind}
                            {s.name ? ` · ${s.name}` : ""}
                          </span>
                          <pre>{JSON.stringify(s, null, 2)}</pre>
                        </div>
                      ))}
                      {!replay?.steps?.length ? <p className="muted">无轨迹。</p> : null}
                    </div>
                  </>
                ) : null}
              </section>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
