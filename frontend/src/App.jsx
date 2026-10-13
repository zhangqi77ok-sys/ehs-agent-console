import React, { useState } from "react";
import DomainPanel from "./components/DomainPanel.jsx";
import AgentPanel from "./components/AgentPanel.jsx";
import RuntimePanel from "./components/RuntimePanel.jsx";

const TENANTS = ["demo-plant", "other-plant"];
const ROLES = [
  { value: "ehs_engineer", label: "EHS 工程师（可写）" },
  { value: "viewer", label: "viewer（只读）" },
  { value: "admin", label: "admin（可写+审计）" },
];

const TABS = [
  { id: "domain", label: "Domain 台账" },
  { id: "agent", label: "Agent" },
  { id: "runtime", label: "Runtime" },
];

export default function App() {
  const [tenantId, setTenantId] = useState("demo-plant");
  const [role, setRole] = useState("ehs_engineer");
  const [tab, setTab] = useState("domain");

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <strong>EHS Agent Console</strong>
          <span className="muted">领域台账 + Agent Runtime</span>
        </div>
        <nav className="tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={tab === t.id ? "tab active" : "tab"}
              onClick={() => setTab(t.id)}
              type="button"
            >
              {t.label}
            </button>
          ))}
        </nav>
        <div className="identity">
          <label>
            租户
            <select value={tenantId} onChange={(e) => setTenantId(e.target.value)}>
              {TENANTS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label>
            角色
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>
      {tab === "domain" && <DomainPanel tenantId={tenantId} role={role} />}
      {tab === "agent" && <AgentPanel tenantId={tenantId} role={role} />}
      {tab === "runtime" && <RuntimePanel tenantId={tenantId} role={role} />}
    </div>
  );
}
