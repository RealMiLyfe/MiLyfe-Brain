"use client";

import { useState, useEffect } from "react";
import { schedulerApi, SchedulerJob } from "@/lib/api";

const CRON_PRESETS = [
  { label: "Every hour", value: "0 * * * *" },
  { label: "Every 6 hours", value: "0 */6 * * *" },
  { label: "Daily at 9am", value: "0 9 * * *" },
  { label: "Weekdays at 8am", value: "0 8 * * 1-5" },
  { label: "Weekly (Monday)", value: "0 9 * * 1" },
  { label: "Monthly (1st)", value: "0 9 1 * *" },
];

export default function SchedulerView() {
  const [jobs, setJobs] = useState<SchedulerJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [cron, setCron] = useState("0 9 * * *");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadJobs();
  }, []);

  async function loadJobs() {
    try {
      const data = await schedulerApi.jobs();
      setJobs(data);
    } catch {
      // Handle silently
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;

    setCreating(true);
    try {
      await schedulerApi.create({ title: title.trim(), cron });
      setTitle("");
      setCron("0 9 * * *");
      setShowForm(false);
      await loadJobs();
    } catch {
      // Handle error
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await schedulerApi.delete(id);
      setJobs(jobs.filter((j) => j.id !== id));
    } catch {
      // Handle error
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-[var(--muted-foreground)]">
        Loading scheduler...
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">Scheduler</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 rounded-lg bg-[var(--primary)] text-white text-sm font-medium hover:opacity-90 transition-opacity"
        >
          {showForm ? "Cancel" : "+ New Job"}
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <form
          onSubmit={handleCreate}
          className="mb-6 p-4 rounded-lg border border-[var(--border)] bg-[var(--card)] space-y-4 animate-slide-up"
        >
          <div>
            <label htmlFor="job-title" className="block text-sm font-medium mb-1">
              Job Title
            </label>
            <input
              id="job-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Daily Research Digest"
              className="w-full px-4 py-2.5 rounded-lg bg-[var(--muted)] border border-[var(--border)] text-[var(--foreground)] placeholder-[var(--muted-foreground)] focus:outline-none focus:border-[var(--primary)]"
            />
          </div>

          <div>
            <label htmlFor="job-cron" className="block text-sm font-medium mb-1">
              Schedule
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              {CRON_PRESETS.map((preset) => (
                <button
                  key={preset.value}
                  type="button"
                  onClick={() => setCron(preset.value)}
                  className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                    cron === preset.value
                      ? "bg-[var(--primary)] text-white"
                      : "bg-[var(--muted)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                  }`}
                >
                  {preset.label}
                </button>
              ))}
            </div>
            <input
              id="job-cron"
              type="text"
              value={cron}
              onChange={(e) => setCron(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-[var(--muted)] border border-[var(--border)] text-[var(--foreground)] font-mono text-sm focus:outline-none focus:border-[var(--primary)]"
            />
          </div>

          <button
            type="submit"
            disabled={creating || !title.trim()}
            className="px-5 py-2.5 rounded-lg bg-[var(--primary)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {creating ? "Creating..." : "Create Job"}
          </button>
        </form>
      )}

      {/* Jobs list */}
      {jobs.length === 0 ? (
        <div className="text-center py-12 text-[var(--muted-foreground)]">
          <p className="text-lg mb-1">No scheduled jobs</p>
          <p className="text-sm">Create a job to run playbooks on a schedule.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {jobs.map((job) => (
            <div
              key={job.id}
              className="p-4 rounded-lg border border-[var(--border)] bg-[var(--card)] flex items-center justify-between"
            >
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-medium">{job.title}</h3>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                      job.enabled
                        ? "bg-[var(--success)] bg-opacity-15 text-[var(--success)]"
                        : "bg-[var(--muted)] text-[var(--muted-foreground)]"
                    }`}
                  >
                    {job.enabled ? "Active" : "Disabled"}
                  </span>
                </div>
                <p className="text-xs text-[var(--muted-foreground)] mt-0.5 font-mono">
                  {job.cron}
                </p>
                <p className="text-xs text-[var(--muted-foreground)]">
                  Next: {new Date(job.next_run).toLocaleString()}
                </p>
              </div>
              <button
                onClick={() => handleDelete(job.id)}
                className="p-2 rounded text-[var(--destructive)] hover:bg-[var(--destructive)] hover:bg-opacity-10 transition-colors"
                aria-label={`Delete job ${job.title}`}
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <path d="M2 4h12M5.33 4V2.67a1.33 1.33 0 011.34-1.34h2.66a1.33 1.33 0 011.34 1.34V4m2 0v9.33a1.33 1.33 0 01-1.34 1.34H4.67a1.33 1.33 0 01-1.34-1.34V4h9.34z" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
