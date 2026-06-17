"use client";

import { useState, useEffect } from "react";
import { listPlaybooks, type Playbook, type PlaybookStatus } from "@/lib/api";
import {
  Clock,
  CheckCircle2,
  XCircle,
  Pause,
  Loader2,
  ChevronDown,
  ChevronRight,
  RefreshCw,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx } from "clsx";
import { toast } from "sonner";

export function HistoryView() {
  const [playbooks, setPlaybooks] = useState<Playbook[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchPlaybooks = async () => {
    setIsLoading(true);
    try {
      const data = await listPlaybooks({ limit: 50 });
      setPlaybooks(data);
    } catch {
      toast.error("Failed to load history");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPlaybooks();
  }, []);

  const getStatusIcon = (status: PlaybookStatus) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case "failed":
        return <XCircle className="w-4 h-4 text-red-500" />;
      case "running":
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case "paused":
        return <Pause className="w-4 h-4 text-amber-500" />;
      case "cancelled":
        return <XCircle className="w-4 h-4 text-slate-400" />;
      default:
        return <Clock className="w-4 h-4 text-slate-400" />;
    }
  };

  const getStatusBadge = (status: PlaybookStatus) => {
    const classes = {
      completed: "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400",
      failed: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400",
      running: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
      paused: "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400",
      cancelled: "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400",
      draft: "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400",
    };
    return (
      <span className={clsx("text-xs px-2 py-0.5 rounded-full font-medium", classes[status])}>
        {status}
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">
          Playbook History
        </h2>
        <button onClick={fetchPlaybooks} className="btn-secondary inline-flex items-center gap-2 text-sm">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {playbooks.length === 0 ? (
        <div className="card text-center py-12">
          <Clock className="w-10 h-10 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-500 dark:text-slate-400">
            No playbook history yet
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {playbooks.map((pb) => (
            <motion.div
              key={pb.id}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              className="card hover:border-primary-200 dark:hover:border-primary-800 transition-colors"
            >
              <button
                onClick={() => setExpandedId(expandedId === pb.id ? null : pb.id)}
                className="w-full flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  {getStatusIcon(pb.status)}
                  <div className="text-left">
                    <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                      {pb.title || pb.description?.slice(0, 60) || "Untitled Playbook"}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {new Date(pb.created_at).toLocaleDateString()} at{" "}
                      {new Date(pb.created_at).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {getStatusBadge(pb.status)}
                  {expandedId === pb.id ? (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-slate-400" />
                  )}
                </div>
              </button>

              <AnimatePresence>
                {expandedId === pb.id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="mt-4 pt-3 border-t border-slate-200 dark:border-slate-700 space-y-3">
                      {pb.description && (
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                          {pb.description}
                        </p>
                      )}
                      <div className="flex items-center gap-4 text-xs text-slate-500">
                        <span>Model: <strong>{pb.model}</strong></span>
                        <span>Steps: <strong>{pb.steps?.length || 0}</strong></span>
                        <span>ID: <code className="font-mono text-[10px]">{pb.id.slice(0, 8)}</code></span>
                      </div>
                      {pb.steps && pb.steps.length > 0 && (
                        <div className="space-y-1.5">
                          {pb.steps.map((step) => (
                            <div key={step.id} className="flex items-center gap-2 text-xs">
                              <span
                                className={clsx(
                                  "w-2 h-2 rounded-full",
                                  step.status === "completed" && "bg-green-500",
                                  step.status === "running" && "bg-blue-500 animate-pulse",
                                  step.status === "failed" && "bg-red-500",
                                  step.status === "pending" && "bg-slate-300 dark:bg-slate-600",
                                  step.status === "skipped" && "bg-slate-400"
                                )}
                              />
                              <span className="text-slate-600 dark:text-slate-400">
                                {step.name}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
