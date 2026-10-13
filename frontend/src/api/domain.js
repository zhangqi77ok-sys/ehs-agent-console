const BASE = "";

function headers(identity = {}) {
  const h = { "Content-Type": "application/json" };
  if (identity.tenant_id) h["X-Tenant-Id"] = identity.tenant_id;
  if (identity.role) h["X-Role"] = identity.role;
  return h;
}

async function json(path, options = {}, identity = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { ...headers(identity), ...(options.headers || {}) },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail || data.error || res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export function fetchAuthMeta() {
  return json("/api/auth/meta");
}

export function fetchSummary(identity) {
  return json("/api/domain/summary", {}, identity);
}

export function createTicket(payload, identity) {
  return json("/api/tickets", { method: "POST", body: JSON.stringify(payload) }, identity);
}

export function advanceTicket(ticket_id, payload, identity) {
  return json(
    `/api/tickets/${encodeURIComponent(ticket_id)}/advance`,
    { method: "POST", body: JSON.stringify(payload) },
    identity
  );
}

export function createSession({ tenant_id, role }) {
  return json("/api/sessions", {
    method: "POST",
    body: JSON.stringify({ tenant_id, role }),
  });
}
