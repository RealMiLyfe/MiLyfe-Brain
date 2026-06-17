"use client";

import { useState } from "react";
import { Send, Sparkles, Upload } from "lucide-react";
import { playbookApi } from "@/lib/api";
import { useBrainStore } from "@/lib/store";

const TEMPLATES = [
  { title: "Build a REST API", description: "Create a complete REST API with CRUD operations, authentication, and documentation" },
  { title: "Refactor codebase", description: "Analyze and refactor the current project for better maintainability and performance" },
  { title: "Write tests", description: "Generate comprehensive test suite covering unit, integration, and edge cases" },
  { title: "Set up CI/CD", description: "Configure continuous integration and deployment pipeline with testing and linting" },
  { title: "Create documentation", description: "Generate complete project documentation including README, API docs, and architecture" },
  { title: "Debug & fix issues", description: "Find and fix bugs in the codebase, including error handling improvements" },
];

interface Props { onSubmit: () => void; }

export function PlaybookInput({ onSubmit }: Props) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const setCurrentPlaybook = useBrainStore((s) => s.setCurrentPlaybook);

  const handleSubmit = async () => {
    if (!description.trim()) return;
    setLoading(true);
    try {
      const result = await playbookApi.create({
        title: title || description.slice(0, 50),
        description,
        raw_text: description,
        auto_execute: true,
      });
      setCurrentPlaybook(result);
      onSubmit();
    } catch (err) {
      console.error("Failed to create playbook:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleTemplate = (t: typeof TEMPLATES[0]) => {
    setTitle(t.title);
    setDescription(t.description);
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">What would you like to build?</h1>
        <p className="text-gray-400">Describe your goal in natural language. The AI swarm will handle the rest.</p>
      </div>

      {/* Input Area */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Playbook title (optional)"
          className="w-full bg-transparent border-b border-gray-700 pb-2 mb-4 text-white placeholder-gray-500 focus:outline-none focus:border-brain-500"
        />
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe what you want to accomplish..."
          rows={6}
          className="w-full bg-transparent text-white placeholder-gray-500 resize-none focus:outline-none"
        />
        <div className="flex justify-between items-center mt-4 pt-4 border-t border-gray-800">
          <div className="flex gap-2">
            <button className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-400 hover:text-white bg-gray-800 rounded-lg">
              <Upload className="w-4 h-4" /> Attach files
            </button>
          </div>
          <button
            onClick={handleSubmit}
            disabled={!description.trim() || loading}
            className="flex items-center gap-2 px-6 py-2.5 bg-brain-600 text-white rounded-lg hover:bg-brain-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            {loading ? "Starting..." : "Execute"}
          </button>
        </div>
      </div>

      {/* Templates */}
      <div>
        <h2 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
          <Sparkles className="w-4 h-4" /> Quick-start templates
        </h2>
        <div className="grid grid-cols-2 gap-3">
          {TEMPLATES.map((t) => (
            <button
              key={t.title}
              onClick={() => handleTemplate(t)}
              className="text-left p-4 bg-gray-900 border border-gray-800 rounded-lg hover:border-brain-500/50 hover:bg-gray-800/50 transition-all"
            >
              <p className="text-sm font-medium text-white mb-1">{t.title}</p>
              <p className="text-xs text-gray-500 line-clamp-2">{t.description}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
