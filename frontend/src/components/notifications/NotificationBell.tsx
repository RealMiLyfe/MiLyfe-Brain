"use client";

import { useEffect, useState } from "react";
import { notificationsApi } from "@/lib/api";
import { useBrainStore } from "@/lib/store";

export default function NotificationBell() {
  const { unreadCount, notifications, setNotifications } = useBrainStore();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    notificationsApi.list().then((data) => setNotifications(data)).catch(() => {});
  }, []);

  const markAllRead = async () => {
    await notificationsApi.readAll();
    setNotifications(notifications.map((n) => ({ ...n, read: true })));
  };

  return (
    <div className="relative">
      <button onClick={() => setOpen(!open)} className="relative p-2 text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
        <span className="text-lg">B</span>
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-[var(--destructive)] text-white text-[10px] rounded-full flex items-center justify-center">
            {unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-[var(--card)] border border-[var(--border)] rounded-lg shadow-xl z-50 max-h-96 overflow-auto">
          <div className="flex items-center justify-between p-3 border-b border-[var(--border)]">
            <span className="text-sm font-medium">Notifications</span>
            {unreadCount > 0 && (
              <button onClick={markAllRead} className="text-xs text-[var(--primary)]">Mark all read</button>
            )}
          </div>
          {notifications.length === 0 ? (
            <p className="p-4 text-sm text-[var(--muted-foreground)] text-center">No notifications</p>
          ) : (
            notifications.slice(0, 20).map((n) => (
              <div key={n.id} className={`p-3 border-b border-[var(--border)] text-sm ${!n.read ? "bg-[var(--primary)]/5" : ""}`}>
                <div className="font-medium text-xs">{n.title}</div>
                <div className="text-[var(--muted-foreground)] text-xs mt-0.5">{n.message}</div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
