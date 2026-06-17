"use client";

import { useState } from "react";
import { useStore, type PendingApproval } from "@/lib/store";
import { motion, AnimatePresence } from "framer-motion";
import { ShieldAlert, Check, X, Clock } from "lucide-react";
import { clsx } from "clsx";
import { toast } from "sonner";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8200";

async function approveRequest(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/stream/approve/${id}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to approve");
}

async function denyRequest(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/stream/deny/${id}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to deny");
}

export function ApprovalDialog() {
  const pendingApprovals = useStore((s) => s.pendingApprovals);
  const resolveApproval = useStore((s) => s.resolveApproval);

  if (pendingApprovals.length === 0) return null;

  return (
    <AnimatePresence>
      {pendingApprovals.map((approval) => (
        <ApprovalCard
          key={approval.id}
          approval={approval}
          onResolve={resolveApproval}
        />
      ))}
    </AnimatePresence>
  );
}

function ApprovalCard({
  approval,
  onResolve,
}: {
  approval: PendingApproval;
  onResolve: (id: string) => void;
}) {
  const [loading, setLoading] = useState<"approve" | "deny" | null>(null);

  const handleApprove = async () => {
    setLoading("approve");
    try {
      await approveRequest(approval.id);
      onResolve(approval.id);
      toast.success("Action approved");
    } catch {
      toast.error("Failed to approve action");
    } finally {
      setLoading(null);
    }
  };

  const handleDeny = async () => {
    setLoading("deny");
    try {
      await denyRequest(approval.id);
      onResolve(approval.id);
      toast.info("Action denied");
    } catch {
      toast.error("Failed to deny action");
    } finally {
      setLoading(null);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -20, scale: 0.95 }}
      className="fixed top-20 right-6 z-50 w-96 bg-white dark:bg-slate-800 border border-amber-200 dark:border-amber-700 rounded-xl shadow-2xl p-5"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
          <ShieldAlert className="w-5 h-5 text-amber-600 dark:text-amber-400" />
        </div>
        <div>
          <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-100">
            Approval Required
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {approval.agent_role && (
              <span className="capitalize">{approval.agent_role} agent</span>
            )}
          </p>
        </div>
        <div
          className={clsx(
            "ml-auto text-xs px-2 py-0.5 rounded-full font-medium",
            approval.risk_level === "high" &&
              "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400",
            approval.risk_level === "medium" &&
              "bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400",
            approval.risk_level === "low" &&
              "bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400"
          )}
        >
          {approval.risk_level} risk
        </div>
      </div>

      {/* Action details */}
      <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 mb-4">
        <p className="text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
          Action: <code className="text-primary-600 dark:text-primary-400">{approval.action}</code>
        </p>
        <p className="text-xs text-slate-500 dark:text-slate-400 break-words">
          {approval.description}
        </p>
      </div>

      {/* Timestamp */}
      <div className="flex items-center gap-1 mb-4 text-xs text-slate-400">
        <Clock className="w-3 h-3" />
        <span>
          {new Date(approval.created_at).toLocaleTimeString()}
        </span>
      </div>

      {/* Action buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleDeny}
          disabled={loading !== null}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors text-sm font-medium disabled:opacity-50"
        >
          <X className="w-4 h-4" />
          {loading === "deny" ? "Denying..." : "Deny"}
        </button>
        <button
          onClick={handleApprove}
          disabled={loading !== null}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white transition-colors text-sm font-medium disabled:opacity-50"
        >
          <Check className="w-4 h-4" />
          {loading === "approve" ? "Approving..." : "Approve"}
        </button>
      </div>
    </motion.div>
  );
}
