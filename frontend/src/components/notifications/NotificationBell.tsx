"use client";

import { useState, useRef, useEffect } from "react";
import { useStore } from "@/lib/store";
import { notificationsApi } from "@/lib/api";

export default function NotificationBell() {
  const notifications = useStore((s) => s.notifications);
  const unreadCount = useStore((s) => s.unreadCount);
  const markAllRead = useStore((s) => s.markAllRead);
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function handleMarkAllRead() {
    markAllRead();
    try {
      await notificationsApi.readAll();
    } catch {
      // Best-effort
    }
  }

  const typeIcons: Record<string, string> = {
    info: "ℹ",
    success: "✓",
    warning: "⚠",
    error: "✕",
  };

  const typeColors: Record<string, string> = {
    info: "text-[var(--primary)]",
    success: "text-[var(--success)]",
    warning: "text-[var(--warning)]",
    error: "text-[var(--destructive)]",
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-lg hover:bg-[var(--muted)] transition-colors"
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 20 20"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-[var(--muted-foreground)]"
        >
          <path d="M15 6.667a5 5 0 00-10 0c0 5.833-2.5 7.5-2.5 7.5h15s-2.5-1.667-2.5-7.5z" />
          <path d="M11.442 16.667a1.667 1.667 0 01-2.884 0" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center rounded-full bg-[var(--destructive)] text-white text-[10px] font-bold px-1">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 rounded-xl border border-[var(--border)] bg-[var(--card)] shadow-2xl z-50 animate-slide-up overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
            <h3 className="text-sm font-semibold">Notifications</h3>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs text-[var(--primary)] hover:underline"
              >
                Mark all read
              </button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="p-6 text-center text-sm text-[var(--muted-foreground)]">
                No notifications
              </div>
            ) : (
              notifications.slice(0, 20).map((n) => (
                <div
                  key={n.id}
                  className={`px-4 py-3 border-b border-[var(--border)] last:border-0 hover:bg-[var(--muted)] transition-colors ${
                    !n.read ? "bg-[var(--primary)] bg-opacity-5" : ""
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <span className={`text-sm ${typeColors[n.type] || ""}`}>
                      {typeIcons[n.type] || "•"}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{n.title}</p>
                      <p className="text-xs text-[var(--muted-foreground)] mt-0.5 line-clamp-2">
                        {n.message}
                      </p>
                      <p className="text-[10px] text-[var(--muted-foreground)] mt-1">
                        {new Date(n.created_at).toLocaleTimeString()}
                      </p>
                    </div>
                    {!n.read && (
                      <span className="w-2 h-2 rounded-full bg-[var(--primary)] flex-shrink-0 mt-1.5" />
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
