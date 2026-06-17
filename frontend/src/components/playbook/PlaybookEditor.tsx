"use client";

import { useState } from "react";
import { useStore } from "@/lib/store";
import { createPlaybook, type PlaybookStep } from "@/lib/api";
import { GripVertical, Plus, X, Save, Play } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { clsx } from "clsx";

const AGENT_ROLES = [
  "planner",
  "coder",
  "researcher",
  "writer",
  "reviewer",
  "tester",
  "deployer",
  "designer",
  "data_analyst",
] as const;

const COMPLEXITY = ["light", "medium", "heavy"] as const;

interface EditorStep {
  id: string;
  description: string;
  agent_role: string;
  complexity: string;
}

function generateId() {
  return Math.random().toString(36).slice(2, 10);
}

export function PlaybookEditor() {
  const setPlaybook = useStore((s) => s.setPlaybook);
  const setActiveView = useStore((s) => s.setActiveView);
  const [title, setTitle] = useState("");
  const [steps, setSteps] = useState<EditorStep[]>([
    { id: generateId(), description: "", agent_role: "planner", complexity: "medium" },
  ]);
  const [isSaving, setIsSaving] = useState(false);

  const addStep = () => {
    setSteps([...steps, { id: generateId(), description: "", agent_role: "coder", complexity: "medium" }]);
  };

  const removeStep = (id: string) => {
    if (steps.length <= 1) return;
    setSteps(steps.filter((s) => s.id !== id));
  };

  const updateStep = (id: string, field: keyof EditorStep, value: string) => {
    setSteps(steps.map((s) => (s.id === id ? { ...s, [field]: value } : s)));
  };

  const handleSave = async () => {
    if (!title.trim()) { toast.error("Please add a playbook title"); return; }
    setIsSaving(true);
    try {
      const prompt = steps.map((s, i) => `Step ${i + 1} [${s.agent_role}/${s.complexity}]: ${s.description}`).join("\n");
      const playbook = await createPlaybook({ prompt: `${title}\n${prompt}`, model: "gpt-4o" });
      setPlaybook(playbook);
      toast.success("Playbook saved!");
    } catch { toast.error("Failed to save playbook"); }
    finally { setIsSaving(false); }
  };

  const handleExecute = async () => {
    if (!title.trim()) { toast.error("Please add a playbook title"); return; }
    setIsSaving(true);
    try {
      const prompt = steps.map((s, i) => `Step ${i + 1} [${s.agent_role}/${s.complexity}]: ${s.description}`).join("\n");
      const playbook = await createPlaybook({ prompt: `${title}\n${prompt}`, model: "gpt-4o", auto_execute: true });
      setPlaybook(playbook);
      setActiveView("dashboard");
      toast.success("Playbook executing!");
    } catch { toast.error("Failed to execute playbook"); }
    finally { setIsSaving(false); }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Playbook title..."
        className="w-full px-4 py-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-lg font-semibold focus:outline-none focus:ring-2 focus:ring-primary-500 text-slate-800 dark:text-slate-100 placeholder:text-slate-400"
      />

      <div className="space-y-3">
        <AnimatePresence>
          {steps.map((step, index) => (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="card flex gap-3 items-start"
            >
              <GripVertical className="w-4 h-4 mt-3 text-slate-400 cursor-grab flex-shrink-0" />
              <span className="mt-2.5 text-sm font-bold text-primary-500 flex-shrink-0">{index + 1}</span>
              <div className="flex-1 space-y-2">
                <textarea
                  value={step.description}
                  onChange={(e) => updateStep(step.id, "description", e.target.value)}
                  placeholder="Describe what this step should do..."
                  rows={2}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-md text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary-500 text-slate-700 dark:text-slate-300"
                />
                <div className="flex gap-2">
                  <select
                    value={step.agent_role}
                    onChange={(e) => updateStep(step.id, "agent_role", e.target.value)}
                    className="px-2 py-1 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded text-xs text-slate-700 dark:text-slate-300"
                  >
                    {AGENT_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                  <select
                    value={step.complexity}
                    onChange={(e) => updateStep(step.id, "complexity", e.target.value)}
                    className="px-2 py-1 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded text-xs text-slate-700 dark:text-slate-300"
                  >
                    {COMPLEXITY.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <button onClick={() => removeStep(step.id)} className="mt-2 p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors">
                <X className="w-4 h-4 text-red-400" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <button onClick={addStep} className="w-full py-2 border-2 border-dashed border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-500 dark:text-slate-400 hover:border-primary-400 hover:text-primary-500 transition-colors flex items-center justify-center gap-1">
        <Plus className="w-4 h-4" /> Add Step
      </button>

      <div className="flex gap-3 justify-end">
        <button onClick={handleSave} disabled={isSaving} className="btn-secondary inline-flex items-center gap-2 px-4 py-2">
          <Save className="w-4 h-4" /> Save
        </button>
        <button onClick={handleExecute} disabled={isSaving} className="btn-primary inline-flex items-center gap-2 px-4 py-2">
          <Play className="w-4 h-4" /> Execute
        </button>
      </div>
    </div>
  );
}
