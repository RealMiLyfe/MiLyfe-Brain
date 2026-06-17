"use client";

import { motion } from "framer-motion";

export function PlaybookProgress({ status }: { status: any }) {
  const progress = status?.progress || 0;
  const statusText = status?.status || "pending";

  const statusColors: Record<string, string> = {
    pending: "text-gray-400",
    running: "text-blue-400",
    completed: "text-green-400",
    failed: "text-red-400",
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-400">Progress</span>
        <span className={`text-sm font-medium capitalize ${statusColors[statusText] || "text-gray-400"}`}>
          {statusText}
        </span>
      </div>
      <div className="w-full h-3 bg-gray-800 rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-brain-600 to-brain-400 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${progress * 100}%` }}
          transition={{ duration: 0.5, ease: "easeInOut" }}
        />
      </div>
      <div className="mt-2 flex justify-between text-xs text-gray-500">
        <span>{status?.current_step || "Waiting..."}</span>
        <span>{Math.round(progress * 100)}%</span>
      </div>
    </div>
  );
}
