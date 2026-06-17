"use client";

import { useEffect, useState } from "react";

export default function KeyboardShortcutsHelp() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "?" && !e.ctrlKey && !e.metaKey) {
        const target = e.target as HTMLElement;
        if (target.tagName !== "INPUT" && target.tagName !== "TEXTAREA") {
          setOpen((v) => !v);
        }
      }
    };
    const escHandler = () => setOpen(false);
    window.addEventListener("keydown", handler);
    window.addEventListener("milyfe:escape", escHandler);
    return () => {
      window.removeEventListener("keydown", handler);
      window.removeEventListener("milyfe:escape", escHandler);
    };
  }, []);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={() => setOpen(false)}
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
    >
      <div
        className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-6 w-[480px] max-h-[80vh] overflow-auto shadow-2xl animate-slideUp"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">Keyboard Shortcuts</h2>
          <button onClick={() => setOpen(false)} className="text-[var(--muted-foreground)] hover:text-[var(--foreground)]" aria-label="Close">
            Esc
          </button>
        </div>

        <Section title="Navigation">
          <Shortcut keys="Ctrl+1-8" desc="Switch between views" />
          <Shortcut keys="Ctrl+/" desc="Toggle sidebar" />
          <Shortcut keys="Ctrl+N" desc="New playbook" />
          <Shortcut keys="Ctrl+K" desc="Command palette" />
        </Section>

        <Section title="Actions">
          <Shortcut keys="Ctrl+Enter" desc="Submit / Execute" />
          <Shortcut keys="Escape" desc="Close modal / Cancel" />
        </Section>

        <Section title="Accessibility">
          <Shortcut keys="Alt+S" desc="Skip to main content" />
          <Shortcut keys="Alt+N" desc="Open notifications" />
          <Shortcut keys="?" desc="Toggle this help" />
        </Section>

        <p className="mt-4 text-xs text-[var(--muted-foreground)]">
          Press ? anywhere to toggle this panel
        </p>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <h3 className="text-xs font-medium text-[var(--muted-foreground)] uppercase tracking-wider mb-2">{title}</h3>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

function Shortcut({ keys, desc }: { keys: string; desc: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-[var(--foreground)]">{desc}</span>
      <kbd className="px-2 py-0.5 bg-[var(--muted)] border border-[var(--border)] rounded text-xs font-mono text-[var(--muted-foreground)]">
        {keys}
      </kbd>
    </div>
  );
}
