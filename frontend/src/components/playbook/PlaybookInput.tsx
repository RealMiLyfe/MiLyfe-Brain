"use client";

import { useState } from "react";
import { playbookApi } from "@/lib/api";
import { useBrainStore } from "@/lib/store";

const TEMPLATES = [
  { title: "Build a REST API", desc: "Create a full REST API with CRUD operations" },
  { title: "Organize Files", desc: "Sort and organize files by type and date" },
  { title: "Write Documentation", desc: "Generate comprehensive docs for a project" },
  { title: "Fix a Bug", desc: "Diagnose and fix a bug from an error message" },
  { title: "Code Review", desc: "Review code for quality, security, and performance" },
  { title: "Deploy Project", desc: "Set up Docker deployment for a project" },
];

export default function PlaybookInput() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { setView, setCurrentPlaybook } = useBrainStore();

  const handleSubmit = async () => {
    if (!description.trim()) return;
    setLoading(true);
    setError("");
    try {
      const pb: any = await playbookApi.create({
        title: title || description.slice(0, 50),
        description,
        raw_text: description,
        auto_execute: true,
      });
      setCurrentPlaybook(pb);
      setView("dashboard");
    } catch (e: any) {
      setError(e.message || "Failed to create playbook");
    } finally {
      setLoading(false);
    }
  };

  const applyTemplate = (t: { title: string; desc: string }) => {
    setTitle(t.title);
    setDescription(t.desc);
  };

  return (
    <div className="max-w-4xl mx-auto animate-fadeIn">
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-2">New Playbook</h2>
        <p className="text-[var(--muted-foreground)]">
          Describe what you want to accomplish. The agent swarm will figure out the rest.
        </p>
      </div>

      {/* Input */}
      <div className="space-y-4 mb-6">
        <input
          type="text"
          placeholder="Title (optional)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full px-4 py-2.5 bg-[var(--card)] border border-[var(--border)] rounded-lg text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-[var(--primary)]"
        />
        <textarea
          placeholder="Describe your goal in plain language...&#10;&#10;Examples:&#10;• Build a weather dashboard with React&#10;• Refactor the auth module to use JWT&#10;• Write unit tests for the payment service"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={8}
          className="w-full px-4 py-3 bg-[var(--card)] border border-[var(--border)] rounded-lg text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none focus:border-[var(--primary)] resize-none"
        />
      </div>

      {error && <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">{error}</div>}

      <button
        onClick={handleSubmit}
        disabled={!description.trim() || loading}
        className="w-full py-3 bg-[var(--primary)] text-white font-medium rounded-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
      >
        {loading ? "Launching Swarm..." : "Execute Playbook"}
      </button>

      {/* Templates */}
      <div className="mt-10">
        <h3 className="text-sm font-medium text-[var(--muted-foreground)] mb-3">Quick Start Templates</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {TEMPLATES.map((t) => (
            <button
              key={t.title}
              onClick={() => applyTemplate(t)}
              className="p-3 bg-[var(--card)] border border-[var(--border)] rounded-lg text-left hover:border-[var(--primary)]/50 transition-colors"
            >
              <div className="text-sm font-medium">{t.title}</div>
              <div className="text-xs text-[var(--muted-foreground)] mt-1">{t.desc}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
