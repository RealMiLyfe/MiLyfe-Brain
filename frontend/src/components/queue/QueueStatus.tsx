"use client";

import { useEffect, useState } from "react";
import { Pause, Play, Trash2, RefreshCw } from "lucide-react";
import { queueApi } from "@/lib/api";

export function QueueStatus() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try { setStatus(await queueApi.status()); } catch {}
    setLoading(false);
  };

  useEffect(() => { refresh(); const i = setInterval(refresh, 5000); return () => clearInterval(i); }, []);

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-white">Execution Queue</h1>
        <div className="flex gap-2">
          <button onClick={() => queueApi.pause()} className="flex items-center gap-1 px-3 py-2 bg-yellow-600/20 text-yellow-400 rounded-lg text-sm hover:bg-yellow-600/30">
            <Pause className="w-4 h-4" /> Pause
          </button>
          <button onClick={() => queueApi.resume()} className="flex items-center gap-1 px-3 py-2 bg-green-600/20 text-green-400 rounded-lg text-sm hover:bg-green-600/30">
            <Play className="w-4 h-4" /> Resume
          </button>
          <button onClick={refresh} className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700">
            <RefreshCw className={`w-4 h-4 text-gray-400 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Running */}
      <div className="mb-6">
        <h2 className="text-sm font-medium text-gray-400 mb-2">Currently Running</h2>
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          {status?.running ? (
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
              <span className="text-white text-sm">{status.running.playbook_id}</span>
              <span className="text-gray-500 text-xs ml-auto">{status.running.started_at}</span>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">Nothing running</p>
          )}
        </div>
      </div>

      {/* Waiting */}
      <div className="mb-6">
        <h2 className="text-sm font-medium text-gray-400 mb-2">Waiting ({status?.waiting?.length || 0})</h2>
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          {status?.waiting?.length ? (
            status.waiting.map((item: any, i: number) => (
              <div key={i} className="flex items-center gap-3 py-1">
                <span className="text-gray-500 text-xs">#{item.position}</span>
                <span className="text-gray-300 text-sm">Queued playbook</span>
              </div>
            ))
          ) : (
            <p className="text-gray-500 text-sm">Queue empty</p>
          )}
        </div>
      </div>

      {/* Completed */}
      <div>
        <h2 className="text-sm font-medium text-gray-400 mb-2">Recently Completed ({status?.total_processed || 0} total)</h2>
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 space-y-2">
          {status?.completed?.length ? (
            status.completed.slice(-5).reverse().map((item: any, i: number) => (
              <div key={i} className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${item.status === "completed" ? "bg-green-400" : "bg-red-400"}`} />
                <span className="text-gray-300 text-sm">{item.playbook_id?.slice(0, 8)}</span>
                <span className="text-gray-500 text-xs ml-auto">{item.completed_at}</span>
              </div>
            ))
          ) : (
            <p className="text-gray-500 text-sm">No completed items</p>
          )}
        </div>
      </div>
    </div>
  );
}
