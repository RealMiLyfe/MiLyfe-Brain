"use client";

import { useState, useEffect } from "react";
import { Bell } from "lucide-react";
import { notificationsApi } from "@/lib/api";

export function NotificationBell() {
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await notificationsApi.list(true);
        setUnread(data.length);
        setNotifications(data.slice(0, 5));
      } catch {}
    };
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative">
      <button onClick={() => setOpen(!open)} className="p-2 rounded-lg hover:bg-gray-800 relative">
        <Bell className="w-5 h-5 text-gray-400" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 rounded-full text-[10px] text-white flex items-center justify-center">
            {unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute bottom-full left-0 mb-2 w-72 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50">
          <div className="p-3 border-b border-gray-700 flex justify-between items-center">
            <span className="text-sm font-medium text-white">Notifications</span>
            <button onClick={() => { notificationsApi.readAll(); setUnread(0); }} className="text-xs text-brain-400">
              Mark all read
            </button>
          </div>
          <div className="max-h-60 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="p-4 text-sm text-gray-500 text-center">No notifications</p>
            ) : (
              notifications.map((n) => (
                <div key={n.id} className="p-3 border-b border-gray-700/50 hover:bg-gray-750">
                  <p className="text-sm text-white">{n.title}</p>
                  <p className="text-xs text-gray-400">{n.message}</p>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
