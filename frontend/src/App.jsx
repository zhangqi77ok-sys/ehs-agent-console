import { useEffect, useState } from "react";
import ChatPanel from "./components/ChatPanel.jsx";
import StepsPanel from "./components/StepsPanel.jsx";
import { chatStream } from "./api/chat.js";

const API_BASE = import.meta.env.VITE_API_BASE || "";

function friendlyError(raw) {
  const msg = String(raw || "未知错误");
  if (/OPENAI_API_KEY|api.?key|未配置|missing.*key/i.test(msg)) {
    return `${msg}\n\n提示：检查 backend/.env 的 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL，然后重启 uvicorn。`;
  }
  if (/timeout|超时|Timed out/i.test(msg)) {
    return `${msg}\n\n提示：可调大 LLM_TIMEOUT_S，或用左下角「练习：强制超时」观察重试；正式跑勿勾强制超时。`;
  }
  if (/Failed to fetch|NetworkError|ECONNREFUSED/i.test(msg)) {
    return `${msg}\n\n提示：确认后端已在 :8000 启动（uvicorn app.main:app --reload --port 8000）。`;
  }
  if (/最大步数|预算/i.test(msg)) {
    return `${msg}\n\n提示：问题太大可拆小；或提高 MAX_AGENT_STEPS（默认 8）。`;
  }
  return msg;
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [steps, setSteps] = useState([]);
  const [budget, setBudget] = useState({ used: 0, max: 8, unit: "steps" });
  const [loading, setLoading] = useState(false);
  const [streamingHint, setStreamingHint] = useState("");
  const [reliabilityInfo, setReliabilityInfo] = useState(null);
  const [healthState, setHealthState] = useState("checking"); // checking | ok | down
  const [lastError, setLastError] = useState(null);
  const [runSummary, setRunSummary] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/health`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (cancelled) return;
        if (data) {
          setReliabilityInfo(data);
          setHealthState("ok");
          if (data.max_agent_steps) {
            setBudget((b) => ({ ...b, max: data.max_agent_steps }));
          }
        } else {
          setHealthState("down");
        }
      })
      .catch(() => {
        if (!cancelled) setHealthState("down");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function onClear() {
    if (loading) return;
    setMessages([]);
    setSteps([]);
    setBudget({
      used: 0,
      max: reliabilityInfo?.max_agent_steps || 8,
      unit: "steps",
    });
    setLastError(null);
    setRunSummary(null);
    setStreamingHint("");
  }

  async function onSend(text, opts = {}) {
    const forceTimeout = !!opts.forceTimeout;
    const history = messages
      .filter((m) => !m.error)
      .map((m) => ({
        role: m.role === "assistant" ? "assistant" : "user",
        content: m.content,
      }));

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    setSteps([]);
    setLastError(null);
    setRunSummary(null);
    setBudget({
      used: 0,
      max: reliabilityInfo?.max_agent_steps || 8,
      unit: "steps",
    });
    setStreamingHint(forceTimeout ? "强制超时练习 · 连接中…" : "连接中…");

    try {
      const data = await chatStream(
        text,
        history,
        (eventName, payload) => {
          if (eventName === "step_start") {
            setStreamingHint(`第 ${payload.index} 步决策中…`);
          } else if (eventName === "tool_call") {
            setStreamingHint(`调用工具 ${payload.name}…`);
            setSteps((prev) => [...prev, payload]);
          } else if (eventName === "tool_result") {
            setStreamingHint(`工具 ${payload.name} 返回`);
            setSteps((prev) => [...prev, payload]);
          } else if (eventName === "final") {
            setStreamingHint("生成最终回答…");
            setSteps((prev) => [...prev, payload]);
          } else if (eventName === "budget") {
            setBudget(payload);
          } else if (eventName === "note") {
            if (payload.note === "llm_retry") {
              setStreamingHint(
                `LLM 重试 ${payload.attempt}/${payload.max_attempts}：${payload.reason || ""}`
              );
            } else if (payload.note === "force_timeout_drill") {
              setStreamingHint(payload.detail || "强制超时练习已启用");
            }
            setSteps((prev) => [...prev, payload]);
          } else if (eventName === "error") {
            const detail = payload.detail || "未知错误";
            setStreamingHint(`错误：${detail}`);
            setLastError(friendlyError(detail));
          }
        },
        { force_timeout: forceTimeout }
      );

      const finalBudget = data.budget || {
        used: 0,
        max: reliabilityInfo?.max_agent_steps || 8,
        unit: "steps",
      };
      setBudget(finalBudget);

      const finalSteps = data.steps || [];
      if (finalSteps.length) setSteps(finalSteps);

      const tools = finalSteps
        .filter((s) => s.kind === "tool_call" && s.name)
        .map((s) => s.name);
      const retries = finalSteps.filter(
        (s) => s.kind === "note" && s.note === "llm_retry"
      ).length;
      const ok = data.ok !== false && !String(data.reply || "").startsWith("调用失败：");
      setRunSummary({
        ok,
        tools,
        retries,
        stepsUsed: finalBudget.used,
        stepsMax: finalBudget.max,
      });

      const content = ok
        ? data.reply
        : friendlyError(data.reply || "调用失败");
      if (!ok) setLastError(content);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content,
          error: !ok,
        },
      ]);
    } catch (err) {
      const msg = friendlyError(err.message);
      setLastError(msg);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `请求失败：${msg}`, error: true },
      ]);
      setRunSummary({ ok: false, tools: [], retries: 0, stepsUsed: 0, stepsMax: budget.max });
    } finally {
      setLoading(false);
      setStreamingHint("");
    }
  }

  const provider = reliabilityInfo?.llm_provider || "—";
  const maxSteps = reliabilityInfo?.max_agent_steps ?? budget.max;
  const toolCount = reliabilityInfo?.tool_count;

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <h1>EHS 隐患闭环 Agent 控制台</h1>
          <span className="meta">MVP · 真实 LLM · SSE · FastAPI + React</span>
        </div>
        <div className="header-status" title="来自 GET /health">
          <span className={`chip chip-${healthState}`}>
            {healthState === "ok"
              ? "后端在线"
              : healthState === "checking"
                ? "检测中…"
                : "后端离线"}
          </span>
          <span className="chip">LLM · {provider}</span>
          <span className="chip">预算 · {maxSteps} 步</span>
          {toolCount != null ? <span className="chip">工具 · {toolCount}</span> : null}
          <span className="chip chip-eval" title={reliabilityInfo?.eval_cmd || "python scripts/run_eval.py -v"}>
            评测门禁 · 5 cases
          </span>
        </div>
      </header>
      <div className="main">
        <ChatPanel
          messages={messages}
          loading={loading}
          streamingHint={streamingHint}
          onSend={onSend}
          onClear={onClear}
          reliabilityInfo={reliabilityInfo}
          lastError={lastError}
        />
        <StepsPanel
          steps={steps}
          budget={budget}
          streaming={loading}
          runSummary={runSummary}
        />
      </div>
    </div>
  );
}
