"use client";

import { useState, useEffect } from "react";
import { getQueueStatus, type QueueStatusData, type QueueItem } from "@/lib/api";
import {
  Clock,
  Play,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
  Layers,
} from "lucide-react";
import { motion } from "framer-motion";
import { clsx } from "clsx";
import { toast } from "sonner";

export function QueueStatus() {
  const [queueData, setQueueData] = useState<QueueStatusData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchQueue = async () => {
    try {
      const data = await getQueueStatus();
      setQueueData(data);
    } catch {
      toast.error("Failed to load queue status");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
    const interval = setInterval(fetchQueue, 5000);
    return () => clearInterval(interval);
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-primary-500" />
          <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">
            Task Queue
          </h2>
        </div>
        <button
          onClick={fetchQueue}
          className="btn-secondary inline-flex items-center gap-2 text-sm"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Stats Cards */}
      {queueData && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="Running"
            count={queueData.running}
            icon={Play}
            color="text-blue-500"
            bgColor="bg-blue-100 dark:bg-blue-900/30"
          />
          <StatCard
            label="Waiting"
            count={queueData.waiting}
            icon={Clock}
            color="text-amber-500"
            bgColor="bg-amber-100 dark:bg-amber-900/30"
          />
          <StatCard
            label="Completed"
            count={queueData.completed}
            icon={CheckCircle2}
            color="text-green-500"
            bgColor="bg-green-100 dark:bg-green-900/30"
          />
          <StatCard
            label="Failed"
            count={queueData.failed}
            icon={XCircle}
            color="text-red-500"
            bgColor="bg-red-100 dark:bg-red-900/30"
          />
        </div>
      )}

      {/* Queue Items */}
      <div className="card">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
          Queue Items
        </h3>
        {queueData && queueData.items.length > 0 ? (
          <div className="space-y-2">
            {queueData.items.map((item) => (
              <QueueItemRow key={item.id} item={item} />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-sm text-slate-400">
            Queue is empty
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  count,
  icon: Icon,
  color,
  bgColor,
}: {
  label: string;
  count: number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="card flex items-center gap-3"
    >
      <div className={clsx("w-10 h-10 rounded-lg flex items-center justify-center", bgColor)}>
        <Icon className={clsx("w-5 h-5", color)} />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">
          {count}
        </p>
        <p className="text-xs text-slate-500">{label}</p>
      </div>
    </motion.div>
  );
}

function QueueItemRow({ item }: { item: QueueItem }) {
  const getStatusColor = (status: QueueItem["status"]) => {
    switch (status) {
      case "running":
        return "bg-blue-500";
      case "waiting":
        return "bg-amber-500";
      case "completed":
        return "bg-green-500";
      case "failed":
        return "bg-red-500";
    }
  };

  return (
    <div className="flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
      <span className={clsx("w-2 h-2 rounded-full", getStatusColor(item.status))} />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-slate-700 dark:text-slate-300 truncate">
          {item.type}
        </p>
        <p className="text-[11px] text-slate-400 font-mono">
          {item.id.slice(0, 8)}
        </p>
      </div>
      <div className="text-right">
        <span
          className={clsx(
            "text-[10px] px-1.5 py-0.5 rounded-full font-medium",
            item.status === "running" && "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400",
            item.status === "waiting" && "bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400",
            item.status === "completed" && "bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400",
            item.status === "failed" && "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400"
          )}
        >
          {item.status}
        </span>
        <p className="text-[10px] text-slate-400 mt-0.5">
          P{item.priority}
        </p>
      </div>
    </div>
  );
}
