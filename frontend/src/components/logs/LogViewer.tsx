"use client";

import { useState, useEffect } from "react";
import { logsApi, LogEntry } from "@/lib/api";

const RISK_COLORS: Record<string, string> = {
  low: "text-[var(--success)]",
  medium: "text-[var(--warning)]",
  high: "text-[var(--destructive)]",
  critical: "text-[var(--destructive)] font-bold",
};

export default function LogViewer() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [roleFilter, setRoleFilter] = useState<string>("");
  const [actionFilter, setActionFilter] = useState<string>("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data = await logsApi.list({
          role: roleFilter || undefined,
          action: actionFilter || undefined,
          limit: 100,
        });
        setLogs(data);
      } catch {
        // Handle silently
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [roleFilter, actionFilter]);

  const uniqueRoles = [...new Set(logs.map((l) => l.role))];
  const uniqueActions = [...new Set(logs.map((l) => l.action))];

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">Logs</h2>
        <div className="flex gap-2">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="px-3 py-1.5 rounded bg-[var(--muted)] border border-[var(--border)] text-sm text-[var(--foreground)]"
            aria-label="Filter by role"
          >
            <option value="">All Roles</option>
            {uniqueRoles.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="px-3 py-1.5 rounded bg-[var(--muted)] border border-[var(--border)] text-sm text-[var(--foreground)]"
            aria-label="Filter by action type"
          >
            <option value="">All Actions</option>
            {uniqueActions.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-[var(--muted-foreground)]">
          Loading logs...
        </div>
      ) : logs.length === 0 ? (
        <div className="text-center py-12 text-[var(--muted-foreground)]">
          <p>No logs found.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[var(--muted)] border-b border-[var(--border)]">
                <th className="text-left px-4 py-2.5 font-medium text-[var(--muted-foreground)]">
                  Time
                </th>
                <th className="text-left px-4 py-2.5 font-medium text-[var(--muted-foreground)]">
                  Role
                </th>
                <th className="text-left px-4 py-2.5 font-medium text-[var(--muted-foreground)]">
                  Action
                </th>
                <th className="text-left px-4 py-2.5 font-medium text-[var(--muted-foreground)]">
                  Description
                </th>
                <th className="text-left px-4 py-2.5 font-medium text-[var(--muted-foreground)]">
                  Risk
                </th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr
                  key={log.id}
                  className="border-b border-[var(--border)] hover:bg-[var(--muted)] hover:bg-opacity-50 transition-colors"
                >
                  <td className="px-4 py-2.5 text-[var(--muted-foreground)] whitespace-nowrap">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="px-2 py-0.5 rounded bg-[var(--primary)] bg-opacity-15 text-[var(--primary)] text-xs font-medium">
                      {log.role}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-[var(--foreground)]">
                    {log.action}
                  </td>
                  <td className="px-4 py-2.5 text-[var(--foreground)] max-w-xs truncate">
                    {log.description}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`text-xs font-medium ${
                        RISK_COLORS[log.risk_level] || "text-[var(--muted-foreground)]"
                      }`}
                    >
                      {log.risk_level}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
