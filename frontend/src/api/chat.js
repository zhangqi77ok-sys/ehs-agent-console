const API_BASE = import.meta.env.VITE_API_BASE || "";

export async function chatStream(message, history = [], onEvent, options = {}) {
  const body = {
    message,
    history,
    force_timeout: !!options.force_timeout,
    session_id: options.session_id || null,
    tenant_id: options.tenant_id || "default",
    role: options.role || "ehs_engineer",
  };
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      "X-Tenant-Id": body.tenant_id,
      "X-Role": body.role,
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  if (!res.body) throw new Error("浏览器不支持 ReadableStream / SSE 响应");

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let finalPayload = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    buffer = buffer.replace(/\r\n/g, "\n");

    let sep;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      let eventName = "message";
      const dataLines = [];
      for (const line of raw.split("\n")) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
      }
      if (!dataLines.length) continue;
      let data;
      try {
        data = JSON.parse(dataLines.join("\n"));
      } catch {
        data = { raw: dataLines.join("\n") };
      }
      if (typeof onEvent === "function") onEvent(eventName, data);
      if (eventName === "done") finalPayload = data;
    }
  }
  if (!finalPayload) throw new Error("流结束但未收到 done 事件");
  return finalPayload;
}

export async function chat(message, history = [], onEvent, options = {}) {
  return chatStream(message, history, onEvent, options);
}
