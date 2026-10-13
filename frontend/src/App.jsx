import { useCallback, useEffect, useState } from "react";
import DomainPanel from "./components/DomainPanel.jsx";
import ChatPanel from "./components/ChatPanel.jsx";
import StepsPanel from "./components/StepsPanel.jsx";
import {
  advanceTicket,
  createSession,
  createTicket,
  fetchAuthMeta,
  fetchSummary,
} from "./api/domain.js";
import { chatStream } from "./api/chat.js";

export default function App() {
  const [tab, setTab] = useState("domain");
  const [tenantId, setTenantId] = useState("default");
  const [role, setRole] = useState("ehs_engineer");
  const [authMeta, setAuthMeta] = useState(null);

  // domain
  const [summary, setSummary] = useState(null);
  const [domainLoading, setDomainLoading] = useState(false);
  const [domainError, setDomainError] = useState("");

  // agent
  const [messages, setMessages] = useState([]);
  const [steps, setSteps] = useState([]);
  const [budget, setBudget] = useState(null);
  const [runSummary, setRunSummary] = useState(null);
  const [agentLoading, setAgentLoading] = useState(false);
  const [streamingHint, setStreamingHint] = useState("");
  const [lastError, setLastError] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [health, setHealth] = useState(null);

  const identity = { tenant_id: tenantId, role };

  useEffect(() => {
    fetchAuthMeta().then(setAuthMeta).catch(() => {});
    fetch("/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => {});
  }, []);

  const refreshDomain = useCallback(async () => {
    setDomainLoading(true);
    setDomainError("");
    try {
      setSummary(await fetchSummary(identity));
    } catch (e) {
      setDomainError(e.message || String(e));
    } finally {
      setDomainLoading(false);
    }
  }, [tenantId, role]);

  useEffect(() => {
    refreshDomain();
  }, [refreshDomain]);

  async function ensureSession() {
    if (sessionId) return sessionId;
    const ses = await createSession({ tenant_id: tenantId, role });
    setSessionId(ses.session_id);
    return ses.session_id;
  }

  async function onCreate(payload) {
    setDomainLoading(true);
    setDomainError("");
    try {
      await createTicket(payload, identity);
      await refreshDomain();
    } catch (e) {
      setDomainError(e.message || String(e));
      setDomainLoading(false);
    }
  }

  async function onAdvance(ticketId, payload) {
    setDomainLoading(true);
    setDomainError("");
    try {
      await advanceTicket(ticketId, payload, identity);
      await refreshDomain();
    } catch (e) {
      setDomainError(e.message || String(e));
      setDomainLoading(false);
    }
  }

  async function onSend(text, { forceTimeout } = {}) {
    setAgentLoading(true);
    setLastError("");
    setStreamingHint("连接中…");
    setSteps([]);
    setBudget(null);
    setRunSummary(null);
    setMessages((m) => [...m, { role: "user", content: text }]);
    try {
      const sid = await ensureSession();
      const history = messages.map(({ role, content }) => ({ role, content }));
      const done = await chatStream(
        text,
        history,
        (evt, data) => {
          if (evt === "step_start") setStreamingHint(`步骤 ${data.index}/${data.max}`);
          if (evt === "budget") setBudget(data);
          if (evt === "tool_call" || evt === "tool_result" || evt === "final" || evt === "note") {
            setSteps((s) => [...s, data]);
          }
          if (evt === "error") setLastError(data.detail || "错误");
        },
        {
          force_timeout: forceTimeout,
          session_id: sid,
          tenant_id: tenantId,
          role,
        }
      );
      setMessages((m) => [...m, { role: "assistant", content: done.reply || "" }]);
      setBudget(done.budget || null);
      setRunSummary(done);
      setStreamingHint("");
    } catch (e) {
      setLastError(e.message || String(e));
      setStreamingHint("");
    } finally {
      setAgentLoading(false);
    }
  }

  function onClearChat() {
    setMessages([]);
    setSteps([]);
    setBudget(null);
    setRunSummary(null);
    setLastError("");
    setSessionId("");
  }

  const reliabilityInfo = health
    ? {
        llm_timeout_s: health.llm_timeout_s,
        llm_max_retries: health.llm_max_retries,
        tool_timeout_s: health.tool_timeout_s,
      }
    : null;

  return (
    <div className="shell">
      <div className="topbar">
        <div className="brand">
          <strong>EHS Agent Console</strong>
          <span className="muted">v2 · 第1–9章</span>
        </div>
        <div className="tabs">
          <button
            type="button"
            className={tab === "domain" ? "tab on" : "tab"}
            onClick={() => setTab("domain")}
          >
            领域台账
          </button>
          <button
            type="button"
            className={tab === "agent" ? "tab on" : "tab"}
            onClick={() => setTab("agent")}
          >
            Agent 控制台
          </button>
        </div>
        <div className="identity">
          <label>
            租户
            <select value={tenantId} onChange={(e) => setTenantId(e.target.value)}>
              {Object.keys(authMeta?.tenants || { default: {} }).map((k) => (
                <option key={k} value={k}>
                  {authMeta?.tenants?.[k]?.name || k}
                </option>
              ))}
            </select>
          </label>
          <label>
            角色
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              {Object.keys(authMeta?.roles || { ehs_engineer: {} }).map((k) => (
                <option key={k} value={k}>
                  {authMeta?.roles?.[k]?.label || k}
                </option>
              ))}
            </select>
          </label>
          {sessionId ? (
            <span className="chip" title="多轮会话">
              session {sessionId.slice(0, 10)}…
            </span>
          ) : null}
        </div>
      </div>

      {tab === "domain" ? (
        <DomainPanel
          summary={summary}
          loading={domainLoading}
          error={domainError}
          onRefresh={refreshDomain}
          onCreate={onCreate}
          onAdvance={onAdvance}
        />
      ) : (
        <div className="agent-layout">
          <ChatPanel
            messages={messages}
            loading={agentLoading}
            streamingHint={streamingHint}
            onSend={onSend}
            onClear={onClearChat}
            reliabilityInfo={reliabilityInfo}
            lastError={lastError}
          />
          <StepsPanel
            steps={steps}
            budget={budget}
            streaming={agentLoading}
            runSummary={runSummary}
          />
        </div>
      )}
    </div>
  );
}
