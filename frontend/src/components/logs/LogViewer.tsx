"use client";

import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { logsApi } from "@/lib/api";

export function LogViewer() {
  const [logs, setLogs] = useState<any[]>([]);
  const [filter, setFilter] = useState({ agent_role: "", action_type: "" });
  const [page, setPage] = useState(0);

  const load = async () => {
    try {
      const params: any = { limit: "50" };
      if (filter.agent_role) params.agent_role = filter.agent_role;
      if (filter.action_type) params.action_type = filter.action_type;
      setLogs(await logsApi.list(params));
    } catch {}
  };

  useEffect(() => { load(); }, [page, filter]);

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold text-white">Action Logs</h1>
        <a href={`${process.env.NEXT_PUBLIC_API_URL}/api/logs/export`} className="flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-800 text-gray-300 rounded hover:bg-gray-700">
          <Download className="w-3 h-3" /> Export CSV
        </a>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <select value={filter.agent_role} onChange={(e) => setFilter({ ...filter, agent_role: e.target.value })}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-300 focus:outline-none">
          <option value="">All Roles</option>
          {["orchestrator","researcher","coder","executor","critic","designer","writer","debugger","planner"].map(r => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <select value={filter.action_type} onChange={(e) => setFilter({ ...filter, action_type: e.target.value })}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-300 focus:outline-none">
          <option value="">All Types</option>
          {["file_read","file_write","shell_exec","code_exec","llm_call","web_browse"].map(t => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      {/* Log Table */}
      <div className="flex-1 overflow-y-auto bg-gray-900 border border-gray-800 rounded-xl">
        <table className="w-full text-sm">
          <thead className="bg-gray-800/50 sticky top-0">
            <tr>
              <th className="text-left p-3 text-gray-400 font-medium">Time</th>
              <th className="text-left p-3 text-gray-400 font-medium">Role</th>
              <th className="text-left p-3 text-gray-400 font-medium">Type</th>
              <th className="text-left p-3 text-gray-400 font-medium">Description</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log: any) => (
              <tr key={log.id} className="border-t border-gray-800/50 hover:bg-gray-800/30">
                <td className="p-3 text-gray-500 text-xs">{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : "-"}</td>
                <td className="p-3 text-gray-300">{log.agent_role || "-"}</td>
                <td className="p-3"><span className="px-1.5 py-0.5 bg-gray-800 rounded text-xs text-gray-400">{log.action_type}</span></td>
                <td className="p-3 text-gray-300 truncate max-w-xs">{log.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex justify-center gap-2 mt-4">
        <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
          className="px-3 py-1 text-sm bg-gray-800 text-gray-400 rounded disabled:opacity-50">Prev</button>
        <span className="px-3 py-1 text-sm text-gray-500">Page {page + 1}</span>
        <button onClick={() => setPage(page + 1)} disabled={logs.length < 50}
          className="px-3 py-1 text-sm bg-gray-800 text-gray-400 rounded disabled:opacity-50">Next</button>
      </div>
    </div>
  );
}
