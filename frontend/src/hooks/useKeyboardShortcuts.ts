"use client";

import { useEffect } from "react";
import { useBrainStore, ViewType } from "@/lib/store";

/**
 * Global keyboard shortcuts for MiLyfe Brain.
 *
 * Navigation:
 *   Ctrl+1..8  → Switch views (Playbook, Dashboard, Chat, etc.)
 *   Ctrl+K     → Quick command palette (focus search)
 *   Ctrl+/     → Toggle sidebar
 *
 * Actions:
 *   Ctrl+Enter → Execute/submit (playbook or chat)
 *   Ctrl+N     → New playbook
 *   Escape     → Close modals/panels
 *
 * Accessibility:
 *   Alt+S      → Skip to main content
 *   Alt+N      → Focus notifications
 */

const VIEW_KEYS: Record<string, ViewType> = {
  "1": "playbook",
  "2": "dashboard",
  "3": "chat",
  "4": "queue",
  "5": "scheduler",
  "6": "history",
  "7": "logs",
  "8": "settings",
};

export function useKeyboardShortcuts() {
  const { setView, toggleSidebar } = useBrainStore();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const ctrl = e.ctrlKey || e.metaKey;
      const alt = e.altKey;
      const key = e.key;

      // Don't intercept when typing in inputs
      const target = e.target as HTMLElement;
      const isInput = target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;

      // Ctrl+Number → switch view (works even in inputs)
      if (ctrl && key in VIEW_KEYS) {
        e.preventDefault();
        setView(VIEW_KEYS[key]);
        return;
      }

      // Skip if typing in input (for remaining shortcuts)
      if (isInput && key !== "Escape") return;

      // Ctrl+/ → toggle sidebar
      if (ctrl && key === "/") {
        e.preventDefault();
        toggleSidebar();
        return;
      }

      // Ctrl+K → focus command/search (placeholder for command palette)
      if (ctrl && key === "k") {
        e.preventDefault();
        // Emit custom event for command palette
        window.dispatchEvent(new CustomEvent("milyfe:command-palette"));
        return;
      }

      // Ctrl+N → new playbook
      if (ctrl && key === "n") {
        e.preventDefault();
        setView("playbook");
        return;
      }

      // Escape → close modals
      if (key === "Escape") {
        window.dispatchEvent(new CustomEvent("milyfe:escape"));
        return;
      }

      // Alt+S → skip to main
      if (alt && key === "s") {
        e.preventDefault();
        document.getElementById("main-content")?.focus();
        return;
      }

      // Alt+N → focus notifications
      if (alt && key === "n") {
        e.preventDefault();
        document.getElementById("notification-bell")?.click();
        return;
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [setView, toggleSidebar]);
}

/**
 * Hook for Ctrl+Enter submit behavior in forms.
 */
export function useSubmitShortcut(onSubmit: () => void) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        onSubmit();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onSubmit]);
}
