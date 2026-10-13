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

export function listRuns(identity) {
  return json("/api/runs", {}, identity);
}

export function getRun(runId, identity) {
  return json(`/api/runs/${encodeURIComponent(runId)}`, {}, identity);
}

export function startRun(payload, identity) {
  return json("/api/runs", { method: "POST", body: JSON.stringify(payload) }, identity);
}

export function resumeRun(runId, payload = {}, identity) {
  return json(
    `/api/runs/${encodeURIComponent(runId)}/resume`,
    { method: "POST", body: JSON.stringify(payload) },
    identity
  );
}

export function getTrace(runId, identity) {
  return json(`/api/runs/${encodeURIComponent(runId)}/trace`, {}, identity);
}

export function getReplay(runId, identity) {
  return json(`/api/runs/${encodeURIComponent(runId)}/replay`, {}, identity);
}

export function listApprovals(identity, status = "pending") {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return json(`/api/approvals${q}`, {}, identity);
}

export function decideApproval(approvalId, { approve, note = "" }, identity) {
  return json(
    `/api/approvals/${encodeURIComponent(approvalId)}/decide`,
    { method: "POST", body: JSON.stringify({ approve, note }) },
    identity
  );
}
