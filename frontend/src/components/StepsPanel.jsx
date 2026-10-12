export default function StepsPanel({ steps, budget, streaming, runSummary }) {
  const used = budget?.used ?? 0;
  const max = budget?.max ?? 8;
  const pct = Math.min(100, Math.round((used / Math.max(max, 1)) * 100));
  const nearLimit = used >= Math.max(1, max - 1) && used < max;
  const tripped = used >= max && !streaming;
  const barTone = tripped ? "danger" : nearLimit || pct >= 75 ? "warn" : "ok";

  const toolCalls = (steps || []).filter((s) => s.kind === "tool_call").length;
  const retries = (steps || []).filter(
    (s) => s.kind === "note" && s.note === "llm_retry"
  ).length;

  return (
    <div className="panel">
      <div className="panel-title">
        步骤 · 工具 · 预算
        {streaming ? <span className="live-badge">LIVE</span> : null}
        {!streaming && runSummary ? (
          <span className={`run-badge ${runSummary.ok ? "ok" : "fail"}`}>
            {runSummary.ok ? "本轮完成" : "本轮失败"}
          </span>
        ) : null}
      </div>
      <div className="steps">
        {(!steps || steps.length === 0) && (
          <div className="empty">
            <p>
              尚无步骤。发送消息后，这里会<strong>边跑边刷</strong>{" "}
              <code>tool_call</code> / <code>tool_result</code> / <code>final</code>。
            </p>
            <ul className="empty-list">
              <li>观察工具名与参数是否合理</li>
              <li>看预算条是否逼近上限（熔断）</li>
              <li>强制超时时应出现 <code>llm_retry</code> note</li>
            </ul>
          </div>
        )}
        {steps?.map((s, i) => (
          <div
            className={`step${i === steps.length - 1 && streaming ? " step-new" : ""}`}
            key={i}
          >
            <span className={`kind ${s.kind}`}>
              #{s.index} {s.kind}
              {s.name ? ` · ${s.name}` : ""}
              {s.note === "tool_timeout" ? " · timeout" : ""}
            </span>
            <pre>
              {s.kind === "tool_call" && JSON.stringify(s.arguments ?? {}, null, 2)}
              {s.kind === "tool_result" && JSON.stringify(s.result ?? {}, null, 2)}
              {s.kind === "final" && (s.content || "")}
              {s.kind === "note" &&
                (s.note === "llm_retry"
                  ? `LLM 重试 ${s.attempt}/${s.max_attempts}：${s.reason || ""}`
                  : s.note === "force_timeout_drill"
                    ? s.detail || "练习：强制超时已启用"
                    : JSON.stringify(s, null, 2))}
              {s.kind === "step_start" && "决策中…"}
            </pre>
          </div>
        ))}
      </div>
      <div className={`budget budget-${barTone}`}>
        <div className="budget-row">
          <span>
            步数预算：<strong>{used}</strong> / {max}（{budget?.unit || "steps"}）
            {tripped ? <span className="circuit"> · 已熔断</span> : null}
            {nearLimit && !tripped ? <span className="circuit warn"> · 接近上限</span> : null}
          </span>
          <span className="budget-meta">
            工具 {toolCalls} · 重试 {retries}
          </span>
        </div>
        <div className={`bar bar-${barTone}`}>
          <span style={{ width: `${pct}%` }} />
        </div>
        {runSummary && !streaming ? (
          <div className="run-summary">
            {runSummary.ok ? "✓" : "✗"} 本轮摘要：
            {runSummary.tools.length
              ? ` 调用 ${runSummary.tools.join(" → ")}`
              : " 无工具调用"}
            {runSummary.retries ? ` · LLM 重试 ${runSummary.retries} 次` : ""}
            {` · 步数 ${runSummary.stepsUsed}/${runSummary.stepsMax}`}
          </div>
        ) : null}
      </div>
    </div>
  );
}
