import React, { useRef, useState } from "react";
import { agentChat, agentChatStream } from "../api/agent.js";

export default function AgentPanel({ tenantId, role }) {
  const [input, setInput] = useState("有哪些未闭环隐患？");
  const [messages, setMessages] = useState([]);
  const [steps, setSteps] = useState([]);
  const [budget, setBudget] = useState(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [useSse, setUseSse] = useState(true);
  const [forceTimeout, setForceTimeout] = useState(false);
  const [pauseAfter, setPauseAfter] = useState("");
  const bottomRef = useRef(null);

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setBusy(true);
    setError("");
    setStatus("running");
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setSteps([]);

    const pauseAfterSteps = pauseAfter ? Number(pauseAfter) : null;

    try {
      if (useSse) {
        const live = [];
        const done = await agentChatStream({
          tenantId,
          role,
          message: text,
          history,
          forceTimeout,
          pauseAfterSteps,
          onEvent: (name, data) => {
            if (name === "budget") setBudget(data);
            if (["tool_call", "tool_result", "final", "note"].includes(name)) {
              live.push(data);
              setSteps([...live]);
            }
            if (name === "paused") setStatus(data.status || "paused");
            if (name === "error") setError(data.detail || "error");
          },
        });
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: done?.reply || "(无回复)" },
        ]);
        setSteps(done?.steps || live);
        setBudget(done?.budget || null);
        setStatus(done?.status || "completed");
      } else {
        const res = await agentChat({
          tenantId,
          role,
          message: text,
          history,
          forceTimeout,
          pauseAfterSteps,
        });
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: res.reply || "(无回复)" },
        ]);
        setSteps(res.steps || []);
        setBudget(res.budget || null);
        setStatus(res.status || "completed");
      }
    } catch (e) {
      setError(e.message);
      setStatus("failed");
    } finally {
      setBusy(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  };

  return (
    <div className="panel agent-panel">
      <div className="agent-grid">
        <div className="card chat-card">
          <div className="row between">
            <h2>Agent 对话</h2>
            <div className="row gap">
              <label className="muted small">
                <input
                  type="checkbox"
                  checked={useSse}
                  onChange={(e) => setUseSse(e.target.checked)}
                />{" "}
                SSE
              </label>
              <label className="muted small">
                <input
                  type="checkbox"
                  checked={forceTimeout}
                  onChange={(e) => setForceTimeout(e.target.checked)}
                />{" "}
                强制超时
              </label>
              <label className="muted small">
                pause@
                <input
                  className="narrow"
                  type="number"
                  min="1"
                  placeholder="步"
                  value={pauseAfter}
                  onChange={(e) => setPauseAfter(e.target.value)}
                />
              </label>
            </div>
          </div>
          <p className="muted small">
            工具只调领域层（同 Domain 台账的 CAPA/ACL/审计）。试：「有哪些未闭环隐患」「查灭火器」
            「给 HZ-2026-001 开整改单，措施：更换过期灭火器」
          </p>
          <div className="chat-log">
            {messages.length === 0 && (
              <p className="muted">发送一条消息开始。mock LLM 按关键词路由工具。</p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`bubble ${m.role}`}>
                <div className="bubble-role">{m.role === "user" ? "你" : "Agent"}</div>
                <pre>{m.content}</pre>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
          {error && <p className="error">{error}</p>}
          <div className="chat-input row">
            <textarea
              rows={2}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              placeholder="输入问题…"
            />
            <button disabled={busy} onClick={send}>
              {busy ? "…" : "发送"}
            </button>
          </div>
        </div>

        <div className="card steps-card">
          <h2>Steps / Budget</h2>
          <p className="muted small">
            状态：<strong>{status || "—"}</strong>
            {budget ? ` · 步数 ${budget.used}/${budget.max}` : ""}
          </p>
          <ol className="steps-list">
            {steps.map((s, i) => (
              <li key={i}>
                <span className="tag">{s.kind || s.note || "?"}</span>{" "}
                {s.kind === "tool_call" && (
                  <code>
                    {s.name}({JSON.stringify(s.arguments || {})})
                  </code>
                )}
                {s.kind === "tool_result" && (
                  <code>
                    {s.name} → {JSON.stringify(s.result || {}).slice(0, 180)}
                  </code>
                )}
                {s.kind === "final" && <span>{s.content}</span>}
                {s.kind === "note" && <span className="muted">{s.detail || s.note}</span>}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}
