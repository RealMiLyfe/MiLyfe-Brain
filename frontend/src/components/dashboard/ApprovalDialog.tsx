"use client";

import { useStore, type PendingApproval } from "@/lib/store";
import { ShieldAlert, CheckCircle, XCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx } from "clsx";
import { toast } from "sonner";

interface ApprovalDialogProps {
  approval: PendingApproval | null;
  onClose: () => void;
}

const RISK_COLORS: Record<string, string> = {
  low: "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400",
  medium: "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400",
  high: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400",
  critical: "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400",
};

export function ApprovalDialog({ approval, onClose }: ApprovalDialogProps) {
  const resolveApproval = useStore((s) => s.resolveApproval);

  const handleApprove = () => {
    if (!approval) return;
    resolveApproval(approval.id);
    toast.success("Action approved");
    onClose();
  };

  const handleDeny = () => {
    if (!approval) return;
    resolveApproval(approval.id);
    toast.info("Action denied");
    onClose();
  };

  return (
    <AnimatePresence>
      {approval && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            onClick={(e) => e.stopPropagation()}
            className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl max-w-md w-full p-6 space-y-4"
          >

            {/* Header */}
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
                <ShieldAlert className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-800 dark:text-slate-100">Approval Required</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">Human-in-the-loop check</p>
              </div>
            </div>

            {/* Details */}
            <div className="space-y-3 bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4">
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-500">Action Type</span>
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{approval.action}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-500">Agent</span>
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300 capitalize">{approval.agent_role}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-500">Risk Level</span>
                <span className={clsx("text-xs px-2 py-0.5 rounded-full font-medium capitalize", RISK_COLORS[approval.risk_level])}>
                  {approval.risk_level}
                </span>
              </div>
              <div>
                <span className="text-xs text-slate-500">Description</span>
                <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{approval.description}</p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <button onClick={handleDeny} className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors font-medium text-sm">
                <XCircle className="w-4 h-4" /> Deny
              </button>
              <button onClick={handleApprove} className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-green-600 hover:bg-green-700 text-white font-medium text-sm transition-colors">
                <CheckCircle className="w-4 h-4" /> Approve
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
