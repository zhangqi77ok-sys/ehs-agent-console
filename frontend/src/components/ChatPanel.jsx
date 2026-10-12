import { useState } from "react";

const HINTS = [
  "查一下灭火器相关隐患",
  "有哪些重大隐患？",
  "给 HZ-2026-001 开整改单，措施：更换过期灭火器",
  "隐患闭环的法规要求是什么？",
];

export default function ChatPanel({ messages, loading, onSend }) {
  const [text, setText] = useState("");

  function submit(e) {
    e?.preventDefault();
    const v = text.trim();
    if (!v || loading) return;
    onSend(v);
    setText("");
  }

  return (
    <div className="panel">
      <div className="panel-title">对话</div>
      <div className="chat-log">
        {messages.length === 0 && (
          <div className="empty">问一句隐患相关的问题，右侧会显示 Agent 步骤与工具调用。</div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}${m.error ? " error" : ""}`}>
            {m.content}
          </div>
        ))}
      </div>
      <div className="hints">
        {HINTS.map((h) => (
          <button key={h} type="button" disabled={loading} onClick={() => onSend(h)}>
            {h}
          </button>
        ))}
      </div>
      <form className="composer" onSubmit={submit}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="例如：查待整改隐患 / 开整改单…"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !text.trim()}>
          {loading ? "思考中…" : "发送"}
        </button>
      </form>
    </div>
  );
}
