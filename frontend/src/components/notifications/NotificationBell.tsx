"use client";

import { useState, useEffect, useRef } from "react";
import { getNotifications, markAllRead, type Notification } from "@/lib/api";
import { useStore } from "@/lib/store";
import { Bell, Check, Info, AlertTriangle, AlertCircle, CheckCircle2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx } from "clsx";

export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const notifications = useStore((state) => state.notifications);
  const unreadCount = useStore((state) => state.unreadCount);
  const setNotifications = useStore((state) => state.setNotifications);
  const markAllNotificationsRead = useStore((state) => state.markAllNotificationsRead);

  // Fetch notifications
  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await getNotifications({ limit: 20 });
        setNotifications(data);
      } catch {
        // Silently fail
      }
    };
    fetch();
    const interval = setInterval(fetch, 30000);
    return () => clearInterval(interval);
  }, [setNotifications]);

  // Close on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleMarkAllRead = async () => {
    try {
      await markAllRead();
      markAllNotificationsRead();
    } catch {
      // Silently fail
    }
  };

  const getIcon = (type: Notification["type"]) => {
    switch (type) {
      case "success":
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case "error":
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case "warning":
        return <AlertTriangle className="w-4 h-4 text-amber-500" />;
      default:
        return <Info className="w-4 h-4 text-blue-500" />;
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative w-9 h-9 rounded-lg flex items-center justify-center text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-red-500 text-white text-[10px] flex items-center justify-center font-medium">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -5, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -5, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full mt-2 w-80 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl overflow-hidden z-50"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700">
              <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                Notifications
              </h4>
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="text-xs text-primary-500 hover:text-primary-600 flex items-center gap-1"
                >
                  <Check className="w-3 h-3" />
                  Mark all read
                </button>
              )}
            </div>

            {/* Notifications list */}
            <div className="max-h-80 overflow-y-auto scrollbar-thin">
              {notifications.length > 0 ? (
                notifications.slice(0, 10).map((notif) => (
                  <div
                    key={notif.id}
                    className={clsx(
                      "flex items-start gap-3 px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors border-b border-slate-100 dark:border-slate-700/50 last:border-0",
                      !notif.read && "bg-primary-50/30 dark:bg-primary-900/10"
                    )}
                  >
                    <div className="flex-shrink-0 mt-0.5">{getIcon(notif.type)}</div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-slate-800 dark:text-slate-200 truncate">
                        {notif.title}
                      </p>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 mt-0.5">
                        {notif.message}
                      </p>
                      <p className="text-[10px] text-slate-400 mt-1">
                        {new Date(notif.created_at).toLocaleTimeString()}
                      </p>
                    </div>
                    {!notif.read && (
                      <span className="w-2 h-2 rounded-full bg-primary-500 flex-shrink-0 mt-1.5" />
                    )}
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-sm text-slate-400">
                  No notifications
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
