"use client";

import { useState } from "react";
import { createPlaybook } from "@/lib/api";
import { useStore } from "@/lib/store";
import {
  Play,
  Sparkles,
  Code,
  FileText,
  Globe,
  TestTube,
  Rocket,
  Bug,
  LayoutGrid,
} from "lucide-react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { clsx } from "clsx";
import { VoiceInput } from "./VoiceInput";
import { GuidedTemplates } from "./GuidedTemplates";

const QUICK_TEMPLATES = [
  {
    label: "Build Feature",
    icon: Code,
    prompt: "Build a new feature that...",
    color: "text-agent-coder",
  },
  {
    label: "Write Docs",
    icon: FileText,
    prompt: "Write comprehensive documentation for...",
    color: "text-agent-writer",
  },
  {
    label: "Research Topic",
    icon: Globe,
    prompt: "Research and summarize information about...",
    color: "text-agent-researcher",
  },
  {
    label: "Write Tests",
    icon: TestTube,
    prompt: "Write unit and integration tests for...",
    color: "text-agent-tester",
  },
  {
    label: "Deploy App",
    icon: Rocket,
    prompt: "Deploy the application to production with...",
    color: "text-agent-deployer",
  },
  {
    label: "Fix Bug",
    icon: Bug,
    prompt: "Investigate and fix the bug where...",
    color: "text-agent-reviewer",
  },
];

const MODELS = [
  { id: "phi3:mini", label: "Phi-3 Mini (Fast)", tier: "light" },
  { id: "llama3.1:8b", label: "Llama 3.1 8B (Balanced)", tier: "heavy" },
  { id: "llama3.1:70b", label: "Llama 3.1 70B (Premium)", tier: "premium" },
  { id: "qwen2.5:14b", label: "Qwen 2.5 14B", tier: "heavy" },
  { id: "hermes3:latest", label: "Hermes 3 (Creative)", tier: "heavy" },
  { id: "gemma2:9b", label: "Gemma 2 9B", tier: "heavy" },
];

export function PlaybookInput() {
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState("llama3.1:8b");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const setPlaybook = useStore((state) => state.setPlaybook);
  const setActiveView = useStore((state) => state.setActiveView);
  const [showGuidedTemplates, setShowGuidedTemplates] = useState(false);

  const handleSubmit = async () => {
    if (!prompt.trim()) {
      toast.error("Please enter a playbook description");
      return;
    }

    setIsSubmitting(true);
    try {
      const playbook = await createPlaybook({
        prompt: prompt.trim(),
        model,
        auto_execute: true,
      });
      setPlaybook(playbook);
      setActiveView("dashboard");
      toast.success("Playbook created and executing!");
      setPrompt("");
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to create playbook"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTemplateClick = (template: string) => {
    setPrompt(template);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="text-center space-y-2">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-center gap-2"
        >
          <Sparkles className="w-6 h-6 text-primary-500" />
          <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
            Create Playbook
          </h2>
        </motion.div>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Describe what you want your AI agents to accomplish
        </p>
      </div>

      {/* Quick Templates */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-2 md:grid-cols-3 gap-3"
      >
        {QUICK_TEMPLATES.map((template) => {
          const Icon = template.icon;
          return (
            <button
              key={template.label}
              onClick={() => handleTemplateClick(template.prompt)}
              className="card hover:border-primary-300 dark:hover:border-primary-600 transition-all duration-200 text-left group"
            >
              <div className="flex items-center gap-2">
                <Icon
                  className={clsx("w-4 h-4 flex-shrink-0", template.color)}
                />
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                  {template.label}
                </span>
              </div>
            </button>
          );
        })}
      </motion.div>

      {/* Main Input */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="card space-y-4"
      >
        <div className="flex items-start gap-2">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe your task in natural language. Be as detailed as you'd like — the AI will plan the steps, spawn the right agents, and execute."
            className="flex-1 h-40 p-4 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all placeholder:text-slate-400 dark:placeholder:text-slate-500 font-mono"
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                handleSubmit();
              }
            }}
          />
          <div className="flex flex-col gap-2 pt-2">
            <VoiceInput onTranscript={(text) => setPrompt((prev) => prev ? prev + " " + text : text)} disabled={isSubmitting} />
          </div>
        </div>

        {/* Bottom bar */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Model selector */}
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 text-slate-700 dark:text-slate-300"
            >
              {MODELS.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
            <button
              onClick={() => setShowGuidedTemplates(!showGuidedTemplates)}
              className="btn-secondary inline-flex items-center gap-1.5 text-sm"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              Templates
            </button>
            <span className="text-xs text-slate-400">
              {prompt.length > 0 && `${prompt.length} chars`}
            </span>
          </div>

          <button
            onClick={handleSubmit}
            disabled={isSubmitting || !prompt.trim()}
            className={clsx(
              "btn-primary inline-flex items-center gap-2",
              (isSubmitting || !prompt.trim()) && "opacity-50 cursor-not-allowed"
            )}
          >
            <Play className="w-4 h-4" />
            {isSubmitting ? "Executing..." : "Execute"}
            {!isSubmitting && (
              <span className="text-xs opacity-60 ml-1">Ctrl+Enter</span>
            )}
          </button>
        </div>
      </motion.div>

      {/* Guided Templates Panel */}
      {showGuidedTemplates && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="overflow-hidden"
        >
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                Guided Templates
              </h3>
              <button
                onClick={() => setShowGuidedTemplates(false)}
                className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              >
                Close
              </button>
            </div>
            <GuidedTemplates onSelect={(p) => { setPrompt(p); setShowGuidedTemplates(false); }} />
          </div>
        </motion.div>
      )}
    </div>
  );
}
