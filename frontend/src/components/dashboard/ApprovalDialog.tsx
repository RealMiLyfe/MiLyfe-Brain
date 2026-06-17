"use client";

import { motion, AnimatePresence } from "framer-motion";
import { ShieldAlert, Check, X } from "lucide-react";
import { useBrainStore } from "@/lib/store";
import { WebSocketClient } from "@/lib/api";
import { AgentAvatar } from "@/components/agents/AgentAvatar";

const RISK_COLORS: Record<string, string> = {
  safe: "text-green-400 bg-green-500/10 border-green-500/30",
  caution: "text-yellow-400 bg-yellow-500/10 border-yellow-500/30",
  dangerous: "text-red-400 bg-red-500/10 border-red-500/30",
};

export function ApprovalDialog() {
  const pendingApprovals = useBrainStore((s) => s.pendingApprovals);
  const removeApproval = useBrainStore((s) => s.removeApproval);

  const handleResponse = (approvalId: string, approved: boolean) => {
    // Send via WebSocket
    const ws = new WebSocketClient();
    ws.connect();
    ws.send({
      type: "approval_response",
      approval_id: approvalId,
      approved,
      reason: approved ? "User approved" : "User denied",
    });
    removeApproval(approvalId);
  };

  if (pendingApprovals.length === 0) return null;

  return (
    <AnimatePresence>
      {pendingApprovals.map((approval) => (
        <motion.div
          key={approval.id}
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          className="fixed bottom-6 right-6 z-50 w-96 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className={`px-4 py-3 border-b border-gray-800 flex items-center gap-3 ${RISK_COLORS[approval.risk_level] || RISK_COLORS.caution}`}>
            <ShieldAlert className="w-5 h-5" />
            <span className="font-medium text-sm">Approval Required</span>
            <span className="ml-auto text-xs uppercase opacity-75">{approval.risk_level}</span>
          </div>

          {/* Body */}
          <div className="p-4 space-y-3">
            {/* Agent info */}
            <div className="flex items-center gap-2">
              <AgentAvatar role={approval.agent_role} size="sm" />
              <span className="text-sm text-gray-300 capitalize">{approval.agent_role}</span>
              <span className="text-xs text-gray-500">wants to execute:</span>
            </div>

            {/* Action */}
            <div className="bg-gray-800 rounded-lg p-3">
              <p className="text-sm text-white font-mono">{approval.action_type}</p>
              <p className="text-xs text-gray-400 mt-1">{approval.description}</p>
              {approval.details && Object.keys(approval.details).length > 0 && (
                <pre className="mt-2 text-xs text-gray-500 overflow-x-auto max-h-24">
                  {JSON.stringify(approval.details, null, 2)}
                </pre>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-2 pt-1">
              <button
                onClick={() => handleResponse(approval.id, true)}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                <Check className="w-4 h-4" /> Approve
              </button>
              <button
                onClick={() => handleResponse(approval.id, false)}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                <X className="w-4 h-4" /> Deny
              </button>
            </div>
          </div>
        </motion.div>
      ))}
    </AnimatePresence>
  );
}
