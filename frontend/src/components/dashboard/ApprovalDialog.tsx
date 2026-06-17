"use client";

import { useBrainStore, ApprovalRequest } from "@/lib/store";

export default function ApprovalDialog() {
  const { pendingApprovals, removeApproval } = useBrainStore();

  if (pendingApprovals.length === 0) return null;

  const approval = pendingApprovals[0]; // Show one at a time

  const handleResolve = (approved: boolean) => {
    // Send approval via WebSocket
    try {
      const ws = (window as any).__milyfe_ws;
      if (ws) {
        ws.send(JSON.stringify({
          type: "approve",
          approval_id: approval.id,
          approved,
          reason: approved ? "" : "User denied",
        }));
      }
    } catch {}
    removeApproval(approval.id);
  };

  const riskColors: Record<string, string> = {
    safe: "text-green-400 bg-green-500/10 border-green-500/30",
    caution: "text-yellow-400 bg-yellow-500/10 border-yellow-500/30",
    dangerous: "text-red-400 bg-red-500/10 border-red-500/30",
    blocked: "text-red-600 bg-red-600/10 border-red-600/30",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Approval required">
      <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-6 w-[500px] max-w-[90vw] shadow-2xl animate-slideUp">
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-yellow-500/20 flex items-center justify-center">
            <span className="text-yellow-400 text-lg">!</span>
          </div>
          <div>
            <h2 className="font-bold text-[var(--foreground)]">Approval Required</h2>
            <p className="text-xs text-[var(--muted-foreground)]">Agent wants to perform a potentially dangerous action</p>
          </div>
        </div>

        {/* Details */}
        <div className="space-y-3 mb-6">
          <div className="flex items-center justify-between">
            <span className="text-sm text-[var(--muted-foreground)]">Action</span>
            <span className="text-sm font-mono">{approval.action_type}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-[var(--muted-foreground)]">Agent</span>
            <span className="text-sm">{approval.agent_role}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-[var(--muted-foreground)]">Risk Level</span>
            <span className={`text-xs px-2 py-0.5 rounded border ${riskColors[approval.risk_level] || ""}`}>
              {approval.risk_level}
            </span>
          </div>
          <div className="p-3 bg-[var(--background)] rounded-lg border border-[var(--border)]">
            <p className="text-sm">{approval.description}</p>
            {approval.details && Object.keys(approval.details).length > 0 && (
              <pre className="text-xs text-[var(--muted-foreground)] mt-2 overflow-auto max-h-32">
                {JSON.stringify(approval.details, null, 2)}
              </pre>
            )}
          </div>
        </div>

        {/* Pending count */}
        {pendingApprovals.length > 1 && (
          <p className="text-xs text-[var(--muted-foreground)] mb-3">+{pendingApprovals.length - 1} more pending</p>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={() => handleResolve(false)}
            className="flex-1 py-2.5 border border-[var(--border)] rounded-lg text-sm hover:bg-[var(--muted)]/50 transition-colors"
          >
            Deny
          </button>
          <button
            onClick={() => handleResolve(true)}
            className="flex-1 py-2.5 bg-[var(--primary)] text-white rounded-lg text-sm hover:opacity-90 transition-opacity"
          >
            Approve
          </button>
        </div>
      </div>
    </div>
  );
}
