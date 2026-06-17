"use client";

import { useState, useEffect } from "react";
import {
  getSchedulerJobs,
  createSchedulerJob,
  updateSchedulerJob,
  deleteSchedulerJob,
  type SchedulerJob,
} from "@/lib/api";
import {
  Calendar,
  Plus,
  Trash2,
  Loader2,
  Clock,
  Power,
  PowerOff,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx } from "clsx";
import { toast } from "sonner";

export function SchedulerView() {
  const [jobs, setJobs] = useState<SchedulerJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newJob, setNewJob] = useState({
    name: "",
    cron_expression: "",
    command: "",
  });
  const [isCreating, setIsCreating] = useState(false);

  const fetchJobs = async () => {
    try {
      const data = await getSchedulerJobs();
      setJobs(data);
    } catch {
      toast.error("Failed to load scheduler jobs");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleCreate = async () => {
    if (!newJob.name || !newJob.cron_expression) {
      toast.error("Name and cron expression are required");
      return;
    }
    setIsCreating(true);
    try {
      const created = await createSchedulerJob({
        name: newJob.name,
        cron_expression: newJob.cron_expression,
        command: newJob.command || undefined,
        enabled: true,
      });
      setJobs((prev) => [...prev, created]);
      setNewJob({ name: "", cron_expression: "", command: "" });
      setShowCreateForm(false);
      toast.success("Job created!");
    } catch {
      toast.error("Failed to create job");
    } finally {
      setIsCreating(false);
    }
  };

  const handleToggle = async (job: SchedulerJob) => {
    try {
      const updated = await updateSchedulerJob(job.id, {
        enabled: !job.enabled,
      });
      setJobs((prev) => prev.map((j) => (j.id === job.id ? updated : j)));
      toast.success(`Job ${updated.enabled ? "enabled" : "disabled"}`);
    } catch {
      toast.error("Failed to update job");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteSchedulerJob(id);
      setJobs((prev) => prev.filter((j) => j.id !== id));
      toast.success("Job deleted");
    } catch {
      toast.error("Failed to delete job");
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Calendar className="w-5 h-5 text-primary-500" />
          <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">
            Scheduler
          </h2>
        </div>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="btn-primary inline-flex items-center gap-2 text-sm"
        >
          <Plus className="w-4 h-4" />
          New Job
        </button>
      </div>

      {/* Create form */}
      <AnimatePresence>
        {showCreateForm && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="card space-y-4">
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                Create Scheduled Job
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                    Job Name
                  </label>
                  <input
                    type="text"
                    value={newJob.name}
                    onChange={(e) =>
                      setNewJob({ ...newJob, name: e.target.value })
                    }
                    placeholder="Daily backup"
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                    Cron Expression
                  </label>
                  <input
                    type="text"
                    value={newJob.cron_expression}
                    onChange={(e) =>
                      setNewJob({ ...newJob, cron_expression: e.target.value })
                    }
                    placeholder="0 0 * * *"
                    className="input-field font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                    Command (optional)
                  </label>
                  <input
                    type="text"
                    value={newJob.command}
                    onChange={(e) =>
                      setNewJob({ ...newJob, command: e.target.value })
                    }
                    placeholder="run backup-playbook"
                    className="input-field font-mono"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setShowCreateForm(false)}
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreate}
                  disabled={isCreating}
                  className="btn-primary text-sm inline-flex items-center gap-2"
                >
                  {isCreating && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Create
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Jobs list */}
      <div className="card">
        {jobs.length > 0 ? (
          <div className="divide-y divide-slate-100 dark:divide-slate-700/50">
            {jobs.map((job) => (
              <div
                key={job.id}
                className="flex items-center justify-between py-3 first:pt-0 last:pb-0"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={clsx(
                      "w-8 h-8 rounded-lg flex items-center justify-center",
                      job.enabled
                        ? "bg-green-100 dark:bg-green-900/30"
                        : "bg-slate-100 dark:bg-slate-700"
                    )}
                  >
                    <Clock
                      className={clsx(
                        "w-4 h-4",
                        job.enabled
                          ? "text-green-500"
                          : "text-slate-400"
                      )}
                    />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                      {job.name}
                    </p>
                    <p className="text-xs font-mono text-slate-400">
                      {job.cron_expression}
                    </p>
                    {job.next_run && (
                      <p className="text-[10px] text-slate-400 mt-0.5">
                        Next: {new Date(job.next_run).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleToggle(job)}
                    className={clsx(
                      "p-1.5 rounded-md transition-colors",
                      job.enabled
                        ? "text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20"
                        : "text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
                    )}
                    title={job.enabled ? "Disable" : "Enable"}
                  >
                    {job.enabled ? (
                      <Power className="w-4 h-4" />
                    ) : (
                      <PowerOff className="w-4 h-4" />
                    )}
                  </button>
                  <button
                    onClick={() => handleDelete(job.id)}
                    className="p-1.5 rounded-md text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <Calendar className="w-10 h-10 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
            <p className="text-sm text-slate-500 dark:text-slate-400">
              No scheduled jobs
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Create a job to run playbooks on a schedule
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
