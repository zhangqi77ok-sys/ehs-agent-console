const BASE = "";

async function json(path, options) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail || data.error || res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export function fetchSummary() {
  return json("/api/domain/summary");
}

export function createTicket({ hazard_id, measures, owner, due_days }) {
  return json("/api/tickets", {
    method: "POST",
    body: JSON.stringify({ hazard_id, measures, owner, due_days }),
  });
}

export function advanceTicket(ticket_id, { action, evidence_note }) {
  return json(`/api/tickets/${encodeURIComponent(ticket_id)}/advance`, {
    method: "POST",
    body: JSON.stringify({ action, evidence_note }),
  });
}
