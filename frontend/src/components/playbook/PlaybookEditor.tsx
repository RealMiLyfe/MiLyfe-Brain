"use client";

import { useState } from "react";
import { Plus, Trash2, GripVertical } from "lucide-react";

interface Step {
  id: string;
  description: string;
  agent_role: string;
}

const ROLES = ["orchestrator", "researcher", "coder", "executor", "critic", "designer", "writer", "debugger", "planner"];

export function PlaybookEditor() {
  const [steps, setSteps] = useState<Step[]>([
    { id: "1", description: "", agent_role: "coder" },
  ]);

  const addStep = () => {
    setSteps([...steps, { id: String(steps.length + 1), description: "", agent_role: "coder" }]);
  };

  const removeStep = (id: string) => {
    setSteps(steps.filter((s) => s.id !== id));
  };

  const updateStep = (id: string, field: string, value: string) => {
    setSteps(steps.map((s) => (s.id === id ? { ...s, [field]: value } : s)));
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-2xl font-bold text-white mb-6">Playbook Editor</h1>

      <div className="space-y-3">
        {steps.map((step, idx) => (
          <div key={step.id} className="flex items-start gap-3 bg-gray-900 border border-gray-800 rounded-lg p-4">
            <GripVertical className="w-4 h-4 text-gray-600 mt-2 cursor-grab" />
            <span className="text-sm text-gray-500 mt-2 w-6">{idx + 1}.</span>
            <div className="flex-1 space-y-2">
              <input
                type="text"
                value={step.description}
                onChange={(e) => updateStep(step.id, "description", e.target.value)}
                placeholder="Describe this step..."
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-brain-500"
              />
              <select
                value={step.agent_role}
                onChange={(e) => updateStep(step.id, "agent_role", e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-300 focus:outline-none"
              >
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <button onClick={() => removeStep(step.id)} className="p-1 text-gray-500 hover:text-red-400">
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>

      <button onClick={addStep} className="mt-4 flex items-center gap-2 px-4 py-2 text-sm text-gray-400 hover:text-white border border-dashed border-gray-700 rounded-lg hover:border-brain-500">
        <Plus className="w-4 h-4" /> Add Step
      </button>
    </div>
  );
}
