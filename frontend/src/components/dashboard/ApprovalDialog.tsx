"use client";

import { useState } from "react";
import { useStore, PendingApproval } from "@/lib/store";

const RISK_COLORS: Record<string, string> = {
  low: "text-[var(--success)] bg-[var(--success)]",
  medium: "text-[var(--warning)] bg-[var(--warning)]",
  high: "text-[var(--destructive)] bg-[var(--destructive)]",
  critical: "text-[var(--destructive)] bg-[var(--destructive)]",
};

interface ApprovalDialogProps {
  approval: PendingApproval;
}

export default function ApprovalDialog({ approval }: ApprovalDialogProps) {
  const removeApproval = useStore((s) => s.removeApproval);
  const [responding, setResponding] = useState(false);

  async function handleApprove() {
    setResponding(true);
    try {
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/playbooks/${approval.playbook_id}/approve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            approval_id: approval.id,
            approved: true,
          }),
        }
      );
      removeApproval(approval.id);
    } catch {
      // Allow user to retry
    } finally {
      setResponding(false);
    }
  }

  async function handleDeny() {
    setResponding(true);
    try {
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/playbooks/${approval.playbook_id}/approve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            approval_id: approval.id,
            approved: false,
          }),
        }
      );
      removeApproval(approval.id);
    } catch {
      // Allow user to retry
    } finally {
      setResponding(false);
    }
  }

  const riskStyle = RISK_COLORS[approval.risk_level] || RISK_COLORS.low;

  return (
    <div
      role="dialog"
      aria-labelledby="approval-title"
      aria-describedby="approval-desc"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60 animate-fade-in"
    >
      <div className="w-full max-w-md mx-4 p-6 rounded-xl bg-[var(--card)] border border-[var(--border)] shadow-2xl animate-slide-up">
        <h3
          id="approval-title"
          className="text-lg font-bold mb-1 flex items-center gap-2"
        >
          <span className="text-[var(--warning)]">⚠</span>
          Approval Required
        </h3>

        <div className="space-y-3 mt-4">
          <div>
            <p className="text-xs text-[var(--muted-foreground)] uppercase tracking-wide">
              Action Type
            </p>
            <p className="text-sm font-medium">{approval.action_type}</p>
          </div>

          <div>
            <p className="text-xs text-[var(--muted-foreground)] uppercase tracking-wide">
              Description
            </p>
            <p id="approval-desc" className="text-sm">
              {approval.description}
            </p>
          </div>

          <div>
            <p className="text-xs text-[var(--muted-foreground)] uppercase tracking-wide">
              Risk Level
            </p>
            <span
              className={`inline-block px-2 py-0.5 rounded text-xs font-medium bg-opacity-15 ${riskStyle}`}
            >
              {approval.risk_level}
            </span>
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={handleDeny}
            disabled={responding}
            className="flex-1 py-2.5 rounded-lg border border-[var(--border)] text-[var(--foreground)] font-medium hover:bg-[var(--muted)] disabled:opacity-50 transition-colors"
          >
            Deny
          </button>
          <button
            onClick={handleApprove}
            disabled={responding}
            className="flex-1 py-2.5 rounded-lg bg-[var(--primary)] text-white font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            Approve
          </button>
        </div>
      </div>
    </div>
  );
}
