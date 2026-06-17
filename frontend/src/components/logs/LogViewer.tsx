"use client";

import { useState, useEffect, useCallback } from "react";
import { getLogs, type LogEntry } from "@/lib/api";
import {
  Search,
  Filter,
  Download,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertCircle,
  Info,
  AlertTriangle,
  Bug,
} from "lucide-react";
import { motion } from "framer-motion";
import { clsx } from "clsx";
import { toast } from "sonner";

const LOG_LEVELS = ["all", "debug", "info", "warning", "error"] as const;
const AGENT_ROLES = [
  "all",
  "planner",
  "coder",
  "reviewer",
  "executor",
  "researcher",
  "writer",
  "tester",
  "deployer",
  "monitor",
] as const;

const PAGE_SIZE = 50;

export function LogViewer() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [level, setLevel] = useState<string>("all");
  const [role, setRole] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: Record<string, string | number> = {
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      };
      if (level !== "all") params.level = level;
      if (role !== "all") params.role = role;
      if (search) params.search = search;

      const data = await getLogs(params as any);
      setLogs(data.logs);
      setTotal(data.total);
    } catch {
      toast.error("Failed to load logs");
    } finally {
      setIsLoading(false);
    }
  }, [page, level, role, search]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handleSearch = () => {
    setSearch(searchInput);
    setPage(0);
  };

  const handleExport = () => {
    const content = logs
      .map(
        (l) =>
          `[${l.timestamp}] [${l.level.toUpperCase()}] ${l.role ? `[${l.role}]` : ""} ${l.message}`
      )
      .join("\n");
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `logs-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Logs exported!");
  };

  const getLevelIcon = (lvl: string) => {
    switch (lvl) {
      case "error":
        return <AlertCircle className="w-3.5 h-3.5 text-red-500" />;
      case "warning":
        return <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />;
      case "info":
        return <Info className="w-3.5 h-3.5 text-blue-500" />;
      case "debug":
        return <Bug className="w-3.5 h-3.5 text-slate-400" />;
      default:
        return <Info className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">
          Logs
        </h2>
        <div className="flex items-center gap-2">
          <button onClick={fetchLogs} className="btn-secondary text-sm inline-flex items-center gap-1.5">
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
          <button onClick={handleExport} className="btn-secondary text-sm inline-flex items-center gap-1.5">
            <Download className="w-3.5 h-3.5" />
            Export
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="flex-1 min-w-[200px] relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Search logs..."
              className="input-field pl-9"
            />
          </div>

          {/* Level filter */}
          <div className="flex items-center gap-1.5">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={level}
              onChange={(e) => { setLevel(e.target.value); setPage(0); }}
              className="px-2 py-1.5 text-xs bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-md"
            >
              {LOG_LEVELS.map((l) => (
                <option key={l} value={l}>
                  {l === "all" ? "All Levels" : l.charAt(0).toUpperCase() + l.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Role filter */}
          <select
            value={role}
            onChange={(e) => { setRole(e.target.value); setPage(0); }}
            className="px-2 py-1.5 text-xs bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-md"
          >
            {AGENT_ROLES.map((r) => (
              <option key={r} value={r}>
                {r === "all" ? "All Roles" : r.charAt(0).toUpperCase() + r.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Log entries */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center py-12 text-sm text-slate-400">
            No logs found
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-700/50">
            {logs.map((log) => (
              <motion.div
                key={log.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-start gap-3 py-2 px-3 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors"
              >
                {getLevelIcon(log.level)}
                <span className="text-[11px] text-slate-400 font-mono whitespace-nowrap mt-0.5">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                {log.role && (
                  <span className="text-[11px] font-medium text-primary-500 capitalize whitespace-nowrap mt-0.5">
                    [{log.role}]
                  </span>
                )}
                <span className="text-xs text-slate-700 dark:text-slate-300 break-all">
                  {log.message}
                </span>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-500">
            Showing {page * PAGE_SIZE + 1}-{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-30"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs text-slate-500">
              Page {page + 1} of {totalPages}
            </span>
            <button
              onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
              disabled={page >= totalPages - 1}
              className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-30"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
