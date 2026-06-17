"use client";

import { useEffect } from "react";
import { useStore, ViewType } from "@/lib/store";

const VIEW_SHORTCUTS: Record<string, ViewType> = {
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
  const setView = useStore((s) => s.setView);
  const toggleSidebar = useStore((s) => s.toggleSidebar);
  const setCommandPaletteOpen = useStore((s) => s.setCommandPaletteOpen);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const isCtrl = e.ctrlKey || e.metaKey;

      // Ctrl+1-8: switch views
      if (isCtrl && VIEW_SHORTCUTS[e.key]) {
        e.preventDefault();
        setView(VIEW_SHORTCUTS[e.key]);
        return;
      }

      // Ctrl+/: toggle sidebar
      if (isCtrl && e.key === "/") {
        e.preventDefault();
        toggleSidebar();
        return;
      }

      // Ctrl+K: command palette
      if (isCtrl && e.key === "k") {
        e.preventDefault();
        setCommandPaletteOpen(true);
        return;
      }

      // Ctrl+N: new playbook (switch to playbook view)
      if (isCtrl && e.key === "n") {
        e.preventDefault();
        setView("playbook");
        return;
      }

      // Escape: close modals
      if (e.key === "Escape") {
        setCommandPaletteOpen(false);
        return;
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [setView, toggleSidebar, setCommandPaletteOpen]);
}
