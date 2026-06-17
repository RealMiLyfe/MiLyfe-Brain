"use client";

import { useState } from "react";

interface Step {
  id: string;
  description: string;
  agent_role: string;
  depends_on: string[];
  complexity: string;
  tools_needed: string[];
}

const ROLES = ["orchestrator","researcher","coder","executor","critic","designer","writer","debugger","planner"];
const COMPLEXITIES = ["light","medium","heavy"];

export default function PlaybookEditor({ steps: initial, onChange }: { steps?: Step[]; onChange?: (steps: Step[]) => void }) {
  const [steps, setSteps] = useState<Step[]>(initial || []);
  const [editingId, setEditingId] = useState<string | null>(null);

  const addStep = () => {
    const newStep: Step = {
      id: `step_${steps.length + 1}`,
      description: "",
      agent_role: "coder",
      depends_on: [],
      complexity: "medium",
      tools_needed: [],
    };
    const updated = [...steps, newStep];
    setSteps(updated);
    setEditingId(newStep.id);
    onChange?.(updated);
  };

  const removeStep = (id: string) => {
    const updated = steps.filter((s) => s.id !== id).map((s) => ({
      ...s,
      depends_on: s.depends_on.filter((d) => d !== id),
    }));
    setSteps(updated);
    onChange?.(updated);
  };

  const updateStep = (id: string, field: keyof Step, value: any) => {
    const updated = steps.map((s) => (s.id === id ? { ...s, [field]: value } : s));
    setSteps(updated);
    onChange?.(updated);
  };

  const moveStep = (idx: number, direction: -1 | 1) => {
    const newIdx = idx + direction;
    if (newIdx < 0 || newIdx >= steps.length) return;
    const updated = [...steps];
    [updated[idx], updated[newIdx]] = [updated[newIdx], updated[idx]];
    setSteps(updated);
    onChange?.(updated);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-[var(--muted-foreground)]">Steps ({steps.length})</h3>
        <button onClick={addStep} className="px-3 py-1.5 text-xs bg-[var(--primary)] text-white rounded-lg hover:opacity-90">
          + Add Step
        </button>
      </div>

      {steps.length === 0 && (
        <p className="text-sm text-[var(--muted-foreground)] text-center py-8">No steps yet. Add one to get started.</p>
      )}

      {steps.map((step, idx) => (
        <div key={step.id} className="bg-[var(--card)] border border-[var(--border)] rounded-lg p-3 animate-fadeIn">
          <div className="flex items-start gap-2">
            {/* Reorder buttons */}
            <div className="flex flex-col gap-0.5 pt-1">
              <button onClick={() => moveStep(idx, -1)} disabled={idx === 0} className="text-[var(--muted-foreground)] hover:text-[var(--foreground)] disabled:opacity-30 text-xs" aria-label="Move up">^</button>
              <button onClick={() => moveStep(idx, 1)} disabled={idx === steps.length - 1} className="text-[var(--muted-foreground)] hover:text-[var(--foreground)] disabled:opacity-30 text-xs" aria-label="Move down">v</button>
            </div>

            {/* Step number */}
            <span className="text-xs font-mono text-[var(--muted-foreground)] pt-2 w-8">{step.id}</span>

            {/* Content */}
            <div className="flex-1 space-y-2">
              {editingId === step.id ? (
                <>
                  <input
                    type="text"
                    value={step.description}
                    onChange={(e) => updateStep(step.id, "description", e.target.value)}
                    placeholder="Step description..."
                    className="w-full px-2 py-1.5 bg-[var(--background)] border border-[var(--border)] rounded text-sm text-[var(--foreground)]"
                    autoFocus
                  />
                  <div className="flex gap-2">
                    <select value={step.agent_role} onChange={(e) => updateStep(step.id, "agent_role", e.target.value)} className="px-2 py-1 bg-[var(--background)] border border-[var(--border)] rounded text-xs text-[var(--foreground)]">
                      {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                    <select value={step.complexity} onChange={(e) => updateStep(step.id, "complexity", e.target.value)} className="px-2 py-1 bg-[var(--background)] border border-[var(--border)] rounded text-xs text-[var(--foreground)]">
                      {COMPLEXITIES.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                    <select
                      multiple
                      value={step.depends_on}
                      onChange={(e) => updateStep(step.id, "depends_on", Array.from(e.target.selectedOptions, (o) => o.value))}
                      className="px-2 py-1 bg-[var(--background)] border border-[var(--border)] rounded text-xs text-[var(--foreground)] max-h-16"
                    >
                      {steps.filter((s) => s.id !== step.id).map((s) => <option key={s.id} value={s.id}>{s.id}</option>)}
                    </select>
                    <button onClick={() => setEditingId(null)} className="px-2 py-1 text-xs text-[var(--primary)]">Done</button>
                  </div>
                </>
              ) : (
                <div className="flex items-center justify-between cursor-pointer" onClick={() => setEditingId(step.id)}>
                  <div>
                    <p className="text-sm">{step.description || <span className="text-[var(--muted-foreground)] italic">Click to edit...</span>}</p>
                    <div className="flex gap-2 mt-1">
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--muted)] text-[var(--muted-foreground)]">{step.agent_role}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--muted)] text-[var(--muted-foreground)]">{step.complexity}</span>
                      {step.depends_on.length > 0 && <span className="text-[10px] text-[var(--muted-foreground)]">depends: {step.depends_on.join(", ")}</span>}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Delete */}
            <button onClick={() => removeStep(step.id)} className="text-red-400 hover:text-red-300 text-xs pt-1" aria-label="Remove step">x</button>
          </div>
        </div>
      ))}
    </div>
  );
}
