import React, { useState } from "react";
import DomainPanel from "./components/DomainPanel.jsx";

const TENANTS = ["demo-plant", "other-plant"];
const ROLES = [
  { value: "ehs_engineer", label: "EHS 工程师（可写）" },
  { value: "viewer", label: "viewer（只读）" },
  { value: "admin", label: "admin（可写+审计）" },
];

export default function App() {
  const [tenantId, setTenantId] = useState("demo-plant");
  const [role, setRole] = useState("ehs_engineer");

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <strong>EHS 领域台账</strong>
          <span className="muted">Ch1 · 无 Agent</span>
        </div>
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
      <DomainPanel tenantId={tenantId} role={role} />
    </div>
  );
}
