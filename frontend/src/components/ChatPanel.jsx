import { useState } from "react";

const HINTS = [
  "查一下灭火器相关隐患",
  "有哪些重大隐患？",
  "给 HZ-2026-001 开整改单，措施：更换过期灭火器",
  "隐患闭环的法规要求是什么？",
];

export default function ChatPanel({
  messages,
  loading,
  streamingHint,
  onSend,
  reliabilityInfo,
}) {
  const [text, setText] = useState("");
  const [forceTimeout, setForceTimeout] = useState(false);

  function submit(e) {
    e?.preventDefault();
    const v = text.trim();
    if (!v || loading) return;
    onSend(v, { forceTimeout });
    setText("");
  }

  function sendHint(h) {
    if (loading) return;
    onSend(h, { forceTimeout });
  }

  const timeoutLabel =
    reliabilityInfo?.llm_timeout_s != null
      ? `${reliabilityInfo.llm_timeout_s}s`
      : "（见 .env LLM_TIMEOUT_S）";
  const retriesLabel =
    reliabilityInfo?.llm_max_retries != null
      ? String(reliabilityInfo.llm_max_retries)
      : "（见 .env）";

  return (
    <div className="panel">
      <div className="panel-title">对话</div>
      <div className="chat-log">
        {messages.length === 0 && (
          <div className="empty">
            问一句隐患相关的问题，右侧会<strong>实时</strong>显示 Agent 步骤与工具调用。
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}${m.error ? " error" : ""}`}>
            {m.content}
          </div>
        ))}
        {loading && streamingHint && (
          <div className="bubble assistant streaming">{streamingHint}</div>
        )}
      </div>
      <div className="hints">
        {HINTS.map((h) => (
          <button key={h} type="button" disabled={loading} onClick={() => sendHint(h)}>
            {h}
          </button>
        ))}
      </div>
      <div className={`drill-bar${forceTimeout ? " active" : ""}`}>
        <label className="drill-toggle">
          <input
            type="checkbox"
            checked={forceTimeout}
            disabled={loading}
            onChange={(e) => setForceTimeout(e.target.checked)}
          />
          <span>练习：强制超时</span>
        </label>
        <span className="drill-hint">
          {forceTimeout
            ? "本轮用 ~0.05s 超时打真实 LLM，右栏应出现 llm_retry / 最终失败"
            : `正常超时 ${timeoutLabel} · 重试 ${retriesLabel} 次`}
        </span>
      </div>
      <form className="composer" onSubmit={submit}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="例如：查待整改隐患 / 开整改单…"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !text.trim()}>
          {loading ? "流式中…" : "发送"}
        </button>
      </form>
    </div>
  );
}
