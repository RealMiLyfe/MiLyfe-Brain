"use client";

import { motion, AnimatePresence } from "framer-motion";
import type { StreamEvent } from "@/lib/store";

const EVENT_COLORS: Record<string, string> = {
  agent_spawned: "text-purple-400",
  thought: "text-blue-400",
  action: "text-yellow-400",
  progress: "text-green-400",
  error: "text-red-400",
  completed: "text-emerald-400",
  step_started: "text-cyan-400",
  step_completed: "text-green-400",
};

export function EventLog({ events }: { events: StreamEvent[] }) {
  const recent = events.slice(-50).reverse();

  return (
    <div className="h-64 overflow-y-auto space-y-1 font-mono text-xs">
      <AnimatePresence>
        {recent.length === 0 ? (
          <p className="text-gray-600 text-center py-8">Waiting for events...</p>
        ) : (
          recent.map((event, i) => (
            <motion.div
              key={`${event.timestamp}-${i}`}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex gap-2 py-0.5"
            >
              <span className="text-gray-600 shrink-0">
                {new Date(event.timestamp).toLocaleTimeString()}
              </span>
              <span className={EVENT_COLORS[event.event_type] || "text-gray-400"}>
                [{event.event_type}]
              </span>
              {event.agent_role && <span className="text-gray-500">{event.agent_role}</span>}
              <span className="text-gray-300 truncate">
                {JSON.stringify(event.data).slice(0, 80)}
              </span>
            </motion.div>
          ))
        )}
      </AnimatePresence>
    </div>
  );
}
