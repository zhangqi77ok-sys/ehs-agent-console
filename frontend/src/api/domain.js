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
    const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export async function listHazards({ tenantId, role, status, level, plant, keyword }) {
  const q = new URLSearchParams();
  if (status) q.set("status", status);
  if (level) q.set("level", level);
  if (plant) q.set("plant", plant);
  if (keyword) q.set("keyword", keyword);
  const qs = q.toString() ? `?${q}` : "";
  return handle(await fetch(`/api/hazards${qs}`, { headers: headers(tenantId, role) }));
}

export async function getHazard(id, { tenantId, role }) {
  return handle(await fetch(`/api/hazards/${id}`, { headers: headers(tenantId, role) }));
}

export async function listTickets({ tenantId, role, hazardId }) {
  const q = hazardId ? `?hazard_id=${encodeURIComponent(hazardId)}` : "";
  return handle(await fetch(`/api/tickets${q}`, { headers: headers(tenantId, role) }));
}

export async function createTicket({ tenantId, role, hazardId, measures, owner, dueDays }) {
  return handle(
    await fetch("/api/tickets", {
      method: "POST",
      headers: headers(tenantId, role),
      body: JSON.stringify({
        hazard_id: hazardId,
        measures,
        owner: owner || null,
        due_days: dueDays ?? 7,
      }),
    })
  );
}

export async function advanceTicket({ tenantId, role, ticketId, action, evidenceNote }) {
  return handle(
    await fetch(`/api/tickets/${ticketId}/advance`, {
      method: "POST",
      headers: headers(tenantId, role),
      body: JSON.stringify({ action, evidence_note: evidenceNote || null }),
    })
  );
}

export async function listAudit({ tenantId, role, limit = 50 }) {
  return handle(
    await fetch(`/api/audit?limit=${limit}`, { headers: headers(tenantId, role) })
  );
}

/** Legal actions by current ticket status (mirrors backend CAPA table). */
export function legalActions(status) {
  switch (status) {
    case "待执行":
      return ["start"];
    case "执行中":
      return ["submit_verify"];
    case "待验收":
      return ["close", "reject"];
    default:
      return [];
  }
}

export const ACTION_LABELS = {
  start: "开始执行",
  submit_verify: "提交验收",
  close: "关闭（需证据）",
  reject: "驳回",
};
