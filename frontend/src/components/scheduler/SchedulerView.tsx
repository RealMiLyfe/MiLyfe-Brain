"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, Clock } from "lucide-react";
import { schedulerApi } from "@/lib/api";

const PRESETS = ["@hourly", "@daily", "@weekly", "*/5 * * * *", "0 9 * * 1-5"];

export function SchedulerView() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [title, setTitle] = useState("");
  const [cron, setCron] = useState("@daily");

  const load = async () => { try { setJobs(await schedulerApi.list()); } catch {} };
  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!title) return;
    await schedulerApi.create({ title, cron_expression: cron });
    setTitle("");
    load();
  };

  const remove = async (id: string) => { await schedulerApi.delete(id); load(); };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-2xl font-bold text-white mb-6">Scheduler</h1>

      {/* Create Job */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-6">
        <div className="flex gap-3">
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Job title"
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-brain-500" />
          <select value={cron} onChange={(e) => setCron(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-300 focus:outline-none">
            {PRESETS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <button onClick={create} className="flex items-center gap-1 px-4 py-2 bg-brain-600 text-white rounded text-sm hover:bg-brain-700">
            <Plus className="w-4 h-4" /> Create
          </button>
        </div>
      </div>

      {/* Job List */}
      <div className="space-y-2">
        {jobs.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Clock className="w-10 h-10 mx-auto mb-3 text-gray-600" />
            <p>No scheduled jobs</p>
          </div>
        ) : (
          jobs.map((job) => (
            <div key={job.id} className="flex items-center gap-3 bg-gray-900 border border-gray-800 rounded-lg p-3">
              <div className={`w-2 h-2 rounded-full ${job.enabled ? "bg-green-400" : "bg-gray-600"}`} />
              <div className="flex-1">
                <p className="text-sm text-white">{job.title}</p>
                <p className="text-xs text-gray-500">{job.cron_expression} | Last: {job.last_run || "Never"}</p>
              </div>
              <button onClick={() => remove(job.id)} className="p-1 text-gray-500 hover:text-red-400">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
