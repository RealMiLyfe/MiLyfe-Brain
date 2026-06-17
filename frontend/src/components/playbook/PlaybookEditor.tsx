"use client";

import { useState } from "react";
import { useStore, PlaybookStep } from "@/lib/store";

const ROLES = [
  "researcher",
  "writer",
  "coder",
  "reviewer",
  "analyst",
  "designer",
  "tester",
  "ops",
];

const COMPLEXITIES: Array<PlaybookStep["complexity"]> = ["low", "medium", "high"];

export default function PlaybookEditor() {
  const currentPlaybook = useStore((s) => s.currentPlaybook);
  const setCurrentPlaybook = useStore((s) => s.setCurrentPlaybook);
  const [editMode, setEditMode] = useState(false);
  const [steps, setSteps] = useState<PlaybookStep[]>(
    currentPlaybook?.steps || []
  );

  function addStep() {
    const newStep: PlaybookStep = {
      id: `step-${Date.now()}`,
      description: "",
      role: ROLES[0],
      complexity: "medium",
      dependencies: [],
      status: "pending",
    };
    setSteps([...steps, newStep]);
  }

  function removeStep(id: string) {
    setSteps(steps.filter((s) => s.id !== id));
  }

  function updateStep(id: string, updates: Partial<PlaybookStep>) {
    setSteps(steps.map((s) => (s.id === id ? { ...s, ...updates } : s)));
  }

  function moveStep(index: number, direction: "up" | "down") {
    const newSteps = [...steps];
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= newSteps.length) return;
    [newSteps[index], newSteps[targetIndex]] = [
      newSteps[targetIndex],
      newSteps[index],
    ];
    setSteps(newSteps);
  }

  function saveSteps() {
    if (currentPlaybook) {
      setCurrentPlaybook({ ...currentPlaybook, steps });
    }
    setEditMode(false);
  }

  if (!currentPlaybook && steps.length === 0) {
    return (
      <div className="text-center text-[var(--muted-foreground)] py-12">
        <p>No playbook loaded. Create one from the Playbook input.</p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Playbook Steps</h3>
        <div className="flex gap-2">
          <button
            onClick={() => setEditMode(!editMode)}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
              editMode
                ? "bg-[var(--primary)] text-white"
                : "bg-[var(--muted)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            }`}
          >
            {editMode ? "Editing" : "Edit"}
          </button>
          {editMode && (
            <button
              onClick={saveSteps}
              className="px-3 py-1.5 rounded text-sm font-medium bg-[var(--success)] text-white"
            >
              Save
            </button>
          )}
        </div>
      </div>

      {/* Steps list */}
      <div className="space-y-3">
        {steps.map((step, index) => (
          <div
            key={step.id}
            className="p-4 rounded-lg border border-[var(--border)] bg-[var(--card)] animate-slide-up"
          >
            <div className="flex items-start gap-3">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[var(--muted)] text-xs font-bold text-[var(--muted-foreground)]">
                {index + 1}
              </span>

              <div className="flex-1 space-y-2">
                {editMode ? (
                  <>
                    <input
                      value={step.description}
                      onChange={(e) =>
                        updateStep(step.id, { description: e.target.value })
                      }
                      placeholder="Step description..."
                      className="w-full px-3 py-2 rounded bg-[var(--muted)] border border-[var(--border)] text-sm text-[var(--foreground)] placeholder-[var(--muted-foreground)]"
                    />
                    <div className="flex gap-3 flex-wrap">
                      <select
                        value={step.role}
                        onChange={(e) =>
                          updateStep(step.id, { role: e.target.value })
                        }
                        className="px-2 py-1 rounded bg-[var(--muted)] border border-[var(--border)] text-xs text-[var(--foreground)]"
                        aria-label="Role"
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>
                            {r}
                          </option>
                        ))}
                      </select>

                      <select
                        value={step.complexity}
                        onChange={(e) =>
                          updateStep(step.id, {
                            complexity: e.target.value as PlaybookStep["complexity"],
                          })
                        }
                        className="px-2 py-1 rounded bg-[var(--muted)] border border-[var(--border)] text-xs text-[var(--foreground)]"
                        aria-label="Complexity"
                      >
                        {COMPLEXITIES.map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>

                      <select
                        multiple
                        value={step.dependencies}
                        onChange={(e) =>
                          updateStep(step.id, {
                            dependencies: Array.from(
                              e.target.selectedOptions,
                              (o) => o.value
                            ),
                          })
                        }
                        className="px-2 py-1 rounded bg-[var(--muted)] border border-[var(--border)] text-xs text-[var(--foreground)] min-w-[120px]"
                        aria-label="Dependencies"
                      >
                        {steps
                          .filter((s) => s.id !== step.id)
                          .map((s, i) => (
                            <option key={s.id} value={s.id}>
                              Step {i + 1}
                            </option>
                          ))}
                      </select>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="text-sm">
                      {step.description || "No description"}
                    </p>
                    <div className="flex gap-2 text-xs">
                      <span className="px-2 py-0.5 rounded bg-[var(--muted)] text-[var(--muted-foreground)]">
                        {step.role}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-[var(--muted)] text-[var(--muted-foreground)]">
                        {step.complexity}
                      </span>
                      {step.dependencies.length > 0 && (
                        <span className="px-2 py-0.5 rounded bg-[var(--muted)] text-[var(--muted-foreground)]">
                          deps: {step.dependencies.length}
                        </span>
                      )}
                    </div>
                  </>
                )}
              </div>

              {editMode && (
                <div className="flex flex-col gap-1">
                  <button
                    onClick={() => moveStep(index, "up")}
                    disabled={index === 0}
                    className="p-1 rounded text-[var(--muted-foreground)] hover:text-[var(--foreground)] disabled:opacity-30"
                    aria-label="Move up"
                  >
                    ↑
                  </button>
                  <button
                    onClick={() => moveStep(index, "down")}
                    disabled={index === steps.length - 1}
                    className="p-1 rounded text-[var(--muted-foreground)] hover:text-[var(--foreground)] disabled:opacity-30"
                    aria-label="Move down"
                  >
                    ↓
                  </button>
                  <button
                    onClick={() => removeStep(step.id)}
                    className="p-1 rounded text-[var(--destructive)] hover:bg-[var(--destructive)] hover:bg-opacity-10"
                    aria-label="Remove step"
                  >
                    ×
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {editMode && (
        <button
          onClick={addStep}
          className="mt-4 w-full py-2.5 rounded-lg border border-dashed border-[var(--border)] text-[var(--muted-foreground)] hover:border-[var(--primary)] hover:text-[var(--primary)] transition-colors text-sm"
        >
          + Add Step
        </button>
      )}
    </div>
  );
}
