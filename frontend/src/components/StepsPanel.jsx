export default function StepsPanel({ steps, budget }) {
  const used = budget?.used ?? 0;
  const max = budget?.max ?? 8;
  const pct = Math.min(100, Math.round((used / max) * 100));

  return (
    <div className="panel">
      <div className="panel-title">步骤 · 工具 · 预算</div>
      <div className="steps">
        {(!steps || steps.length === 0) && (
          <div className="empty">尚无步骤。发送消息后，这里会实时列出 tool_call / tool_result / final。</div>
        )}
        {steps?.map((s, i) => (
          <div className="step" key={i}>
            <span className={`kind ${s.kind}`}>
              #{s.index} {s.kind}
              {s.name ? ` · ${s.name}` : ""}
            </span>
            <pre>
              {s.kind === "tool_call" && JSON.stringify(s.arguments ?? {}, null, 2)}
              {s.kind === "tool_result" && JSON.stringify(s.result ?? {}, null, 2)}
              {s.kind === "final" && (s.content || "")}
            </pre>
          </div>
        ))}
      </div>
      <div className="budget">
        步数预算：<strong>{used}</strong> / {max}（{budget?.unit || "steps"}）
        <div className="bar">
          <span style={{ width: `${pct}%` }} />
        </div>
      </div>
    </div>
  );
}
