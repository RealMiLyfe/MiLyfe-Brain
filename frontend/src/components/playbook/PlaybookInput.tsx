"use client";

import { useState } from "react";
import { playbookApi } from "@/lib/api";
import { useStore } from "@/lib/store";

const QUICK_START_TEMPLATES = [
  {
    title: "Research & Summarize",
    input: "Research the latest trends in AI safety and summarize key findings",
  },
  {
    title: "Code Review",
    input: "Review the codebase for security vulnerabilities and suggest fixes",
  },
  {
    title: "Write Documentation",
    input: "Generate comprehensive API documentation for the backend services",
  },
  {
    title: "Data Analysis",
    input: "Analyze user engagement data and produce an insights report",
  },
  {
    title: "Content Pipeline",
    input: "Create a blog post about local-first AI, including research and editing",
  },
  {
    title: "Test Suite",
    input: "Design and implement integration tests for all API endpoints",
  },
];

export default function PlaybookInput() {
  const [title, setTitle] = useState("");
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const setCurrentPlaybook = useStore((s) => s.setCurrentPlaybook);
  const setView = useStore((s) => s.setView);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) {
      setError("Please describe what you want to accomplish.");
      return;
    }

    setError(null);
    setSubmitting(true);

    try {
      const playbook = await playbookApi.create({
        title: title.trim() || "Untitled Playbook",
        natural_language_input: input.trim(),
      });
      setCurrentPlaybook(playbook);
      setView("dashboard");
      setTitle("");
      setInput("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create playbook");
    } finally {
      setSubmitting(false);
    }
  }

  function applyTemplate(template: (typeof QUICK_START_TEMPLATES)[number]) {
    setTitle(template.title);
    setInput(template.input);
    setError(null);
  }

  return (
    <div className="max-w-3xl mx-auto animate-fade-in">
      <h2 className="text-2xl font-bold mb-2">New Playbook</h2>
      <p className="text-[var(--muted-foreground)] mb-6">
        Describe what you want to accomplish in plain English. MiLyfe Brain will
        orchestrate the right agents to get it done.
      </p>

      {/* Quick-start templates */}
      <div className="mb-6">
        <h3 className="text-sm font-medium text-[var(--muted-foreground)] mb-2">
          Quick Start Templates
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {QUICK_START_TEMPLATES.map((template) => (
            <button
              key={template.title}
              onClick={() => applyTemplate(template)}
              className="text-left p-3 rounded-lg border border-[var(--border)] hover:border-[var(--primary)] hover:bg-[var(--primary)] hover:bg-opacity-5 transition-colors text-sm"
            >
              <span className="font-medium text-[var(--foreground)]">
                {template.title}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Input form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="playbook-title"
            className="block text-sm font-medium mb-1"
          >
            Title
          </label>
          <input
            id="playbook-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Give your playbook a name..."
            className="w-full px-4 py-2.5 rounded-lg bg-[var(--muted)] border border-[var(--border)] text-[var(--foreground)] placeholder-[var(--muted-foreground)] focus:outline-none focus:border-[var(--primary)] transition-colors"
          />
        </div>

        <div>
          <label
            htmlFor="playbook-input"
            className="block text-sm font-medium mb-1"
          >
            Instructions
          </label>
          <textarea
            id="playbook-input"
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              setError(null);
            }}
            placeholder="Describe what you want to accomplish..."
            rows={6}
            className="w-full px-4 py-3 rounded-lg bg-[var(--muted)] border border-[var(--border)] text-[var(--foreground)] placeholder-[var(--muted-foreground)] focus:outline-none focus:border-[var(--primary)] transition-colors resize-y"
          />
        </div>

        {error && (
          <div
            role="alert"
            className="p-3 rounded-lg bg-[var(--destructive)] bg-opacity-10 border border-[var(--destructive)] border-opacity-30 text-[var(--destructive)] text-sm"
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-3 rounded-lg bg-[var(--primary)] text-white font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
        >
          {submitting ? "Creating..." : "Execute Playbook"}
        </button>
      </form>
    </div>
  );
}
