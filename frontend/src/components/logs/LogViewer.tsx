"use client";

import { useEffect, useState } from "react";
import { logsApi } from "@/lib/api";

export default function LogViewer() {
  const [logs, setLogs] = useState<any[]>([]);
  const [filter, setFilter] = useState({ agent_role: "", action_type: "" });

  useEffect(() => {
    const params: Record<string, string> = {};
    if (filter.agent_role) params.agent_role = filter.agent_role;
    if (filter.action_type) params.action_type = filter.action_type;
    logsApi.list(params).then(setLogs).catch(() => {});
  }, [filter]);

  return (
    <div className="animate-fadeIn">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">Action Logs</h2>
        <div className="flex gap-2">
          <select
            value={filter.agent_role}
            onChange={(e) => setFilter((f) => ({ ...f, agent_role: e.target.value }))}
            className="px-3 py-1.5 bg-[var(--card)] border border-[var(--border)] rounded text-sm text-[var(--foreground)]"
          >
            <option value="">All Roles</option>
            {["orchestrator","researcher","coder","executor","critic","designer","writer","debugger","planner"].map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
          <select
            value={filter.action_type}
            onChange={(e) => setFilter((f) => ({ ...f, action_type: e.target.value }))}
            className="px-3 py-1.5 bg-[var(--card)] border border-[var(--border)] rounded text-sm text-[var(--foreground)]"
          >
            <option value="">All Types</option>
            {["file_read","file_write","shell_exec","code_exec","browse_web","llm_call"].map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="bg-[var(--card)] border border-[var(--border)] rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[var(--muted)]/30">
            <tr>
              <th className="px-4 py-2 text-left text-[var(--muted-foreground)]">Time</th>
              <th className="px-4 py-2 text-left text-[var(--muted-foreground)]">Role</th>
              <th className="px-4 py-2 text-left text-[var(--muted-foreground)]">Action</th>
              <th className="px-4 py-2 text-left text-[var(--muted-foreground)]">Description</th>
              <th className="px-4 py-2 text-left text-[var(--muted-foreground)]">Risk</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id} className="border-t border-[var(--border)] hover:bg-[var(--muted)]/20">
                <td className="px-4 py-2 text-xs text-[var(--muted-foreground)]">
                  {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : "-"}
                </td>
                <td className="px-4 py-2">{log.agent_role || "-"}</td>
                <td className="px-4 py-2 font-mono text-xs">{log.action_type}</td>
                <td className="px-4 py-2 max-w-xs truncate">{log.description}</td>
                <td className="px-4 py-2">
                  <RiskBadge level={log.risk_level} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {logs.length === 0 && <p className="p-4 text-center text-[var(--muted-foreground)]">No logs found</p>}
      </div>
    </div>
  );
}

function RiskBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    safe: "text-green-400", caution: "text-yellow-400", dangerous: "text-red-400", blocked: "text-red-600",
  };
  return <span className={`text-xs ${colors[level] || colors.safe}`}>{level}</span>;
}
