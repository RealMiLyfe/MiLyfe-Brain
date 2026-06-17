"use client";

import { useEffect, useState } from "react";
import { schedulerApi } from "@/lib/api";

export default function SchedulerView() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newJob, setNewJob] = useState({ title: "", cron_expression: "@daily" });

  useEffect(() => {
    schedulerApi.jobs().then(setJobs).catch(() => {});
  }, []);

  const createJob = async () => {
    if (!newJob.title) return;
    await schedulerApi.create(newJob);
    setShowCreate(false);
    setNewJob({ title: "", cron_expression: "@daily" });
    schedulerApi.jobs().then(setJobs);
  };

  const deleteJob = async (id: string) => {
    await schedulerApi.delete(id);
    setJobs((j) => j.filter((x) => x.id !== id));
  };

  const PRESETS = ["@hourly", "@daily", "@weekly", "@monthly"];

  return (
    <div className="animate-fadeIn">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">Scheduler</h2>
        <button onClick={() => setShowCreate(!showCreate)} className="px-4 py-2 bg-[var(--primary)] text-white rounded-lg text-sm">
          + New Job
        </button>
      </div>

      {showCreate && (
        <div className="mb-6 p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg space-y-3">
          <input type="text" placeholder="Job title" value={newJob.title} onChange={(e) => setNewJob({ ...newJob, title: e.target.value })} className="w-full px-3 py-2 bg-[var(--background)] border border-[var(--border)] rounded text-sm text-[var(--foreground)]" />
          <div className="flex gap-2">
            {PRESETS.map((p) => (
              <button key={p} onClick={() => setNewJob({ ...newJob, cron_expression: p })} className={`px-3 py-1 rounded text-xs border ${newJob.cron_expression === p ? "border-[var(--primary)] text-[var(--primary)]" : "border-[var(--border)] text-[var(--muted-foreground)]"}`}>
                {p}
              </button>
            ))}
          </div>
          <button onClick={createJob} className="px-4 py-2 bg-[var(--primary)] text-white rounded text-sm">Create</button>
        </div>
      )}

      <div className="space-y-3">
        {jobs.length === 0 ? (
          <p className="text-[var(--muted-foreground)]">No scheduled jobs</p>
        ) : (
          jobs.map((job) => (
            <div key={job.id} className="flex items-center justify-between p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
              <div>
                <h4 className="font-medium text-sm">{job.title}</h4>
                <p className="text-xs text-[var(--muted-foreground)] mt-1">
                  {job.cron_expression} • {job.enabled ? "Enabled" : "Disabled"}
                  {job.last_run && ` • Last: ${new Date(job.last_run).toLocaleDateString()}`}
                </p>
              </div>
              <button onClick={() => deleteJob(job.id)} className="text-xs text-red-400 hover:text-red-300">Delete</button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
