"use client";

import { useEffect, useRef } from "react";
import { useStore } from "@/lib/store";
import { type StreamEvent } from "@/lib/api";
import { Activity, Trash2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx } from "clsx";

const EVENT_COLORS: Record<string, string> = {
  completed: "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400",
  thought: "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400",
  action: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
  error: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400",
  tool_call: "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400",
  status: "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400",
};

export function EventLog() {
  const events = useStore((s) => s.events);
  const clearEvents = useStore((s) => s.clearEvents);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div className="card flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary-500" />
          <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-200">Event Log</h3>
          <span className="text-xs text-slate-400">({events.length})</span>
        </div>
        <button
          onClick={clearEvents}
          className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          title="Clear events"
        >
          <Trash2 className="w-3.5 h-3.5 text-slate-400" />
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto max-h-80 space-y-1 scrollbar-thin">
        {events.length === 0 ? (
          <p className="text-sm text-slate-400 dark:text-slate-500 py-8 text-center">No events yet</p>
        ) : (
          <AnimatePresence initial={false}>
            {events.map((event) => (
              <EventRow key={event.id} event={event} />
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}

function EventRow({ event }: { event: StreamEvent }) {
  const colorClass = EVENT_COLORS[event.type] || EVENT_COLORS.status;

  return (
    <motion.div
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-start gap-2 py-1.5 px-2 rounded text-xs hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors"
    >
      <span className="text-slate-400 dark:text-slate-500 font-mono whitespace-nowrap flex-shrink-0">
        {new Date(event.timestamp).toLocaleTimeString()}
      </span>
      <span className={clsx("px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0", colorClass)}>
        {event.type}
      </span>
      {event.agent_role && (
        <span className="text-primary-500 font-medium capitalize flex-shrink-0">
          {event.agent_role}
        </span>
      )}
      <span className="text-slate-600 dark:text-slate-300 truncate">
        {event.content}
      </span>
    </motion.div>
  );
}
