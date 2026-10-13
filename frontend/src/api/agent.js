function headers(tenantId, role, actor) {
  return {
    "Content-Type": "application/json",
    "X-Tenant-Id": tenantId,
    "X-Role": role,
    "X-Actor": actor || role,
  };
}

async function handle(res) {
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!res.ok) {
    const detail = data?.detail || res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

/** Ch2/Ch11: non-streaming chat */
export async function agentChat({
  tenantId,
  role,
  message,
  history,
  forceTimeout,
  pauseAfterSteps,
  multiAgent,
  sessionId,
}) {
  return handle(
    await fetch("/api/agent/chat", {
      method: "POST",
      headers: headers(tenantId, role),
      body: JSON.stringify({
        message,
        history: history || [],
        force_timeout: !!forceTimeout,
        pause_after_steps: pauseAfterSteps || null,
        multi_agent: !!multiAgent,
        session_id: sessionId || null,
      }),
    })
  );
}

/**
 * Ch3/Ch11: SSE stream. onEvent(eventName, data). Returns final done payload.
 */
export async function agentChatStream({
  tenantId,
  role,
  message,
  history,
  forceTimeout,
  pauseAfterSteps,
  multiAgent,
  sessionId,
  onEvent,
}) {
  const res = await fetch("/api/agent/chat/stream", {
    method: "POST",
    headers: headers(tenantId, role),
    body: JSON.stringify({
      message,
      history: history || [],
      force_timeout: !!forceTimeout,
      pause_after_steps: pauseAfterSteps || null,
      multi_agent: !!multiAgent,
      session_id: sessionId || null,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let donePayload = null;
  let eventName = "message";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n");
    buf = parts.pop() || "";
    for (const line of parts) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        const raw = line.slice(5).trim();
        let data = {};
        try {
          data = JSON.parse(raw);
        } catch {
          data = { raw };
        }
        if (onEvent) onEvent(eventName, data);
        if (eventName === "done") donePayload = data;
        eventName = "message";
      }
    }
  }
  return donePayload;
}
