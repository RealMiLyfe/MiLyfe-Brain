"use client";

import { useState, useEffect } from "react";
import { getSettings, updateSettings, runSelfTest } from "@/lib/api";
import type { Settings, SelfTestResult } from "@/lib/api";
import {
  Save,
  Shield,
  Cpu,
  FlaskConical,
  CheckCircle2,
  XCircle,
  Loader2,
  FolderOpen,
} from "lucide-react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { clsx } from "clsx";

export function SettingsView() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [testResults, setTestResults] = useState<SelfTestResult[] | null>(null);
  const [isRunningTests, setIsRunningTests] = useState(false);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const data = await getSettings();
        setSettings(data);
      } catch {
        toast.error("Failed to load settings");
      } finally {
        setIsLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleSave = async () => {
    if (!settings) return;
    setIsSaving(true);
    try {
      const updated = await updateSettings(settings);
      setSettings(updated);
      toast.success("Settings saved!");
    } catch {
      toast.error("Failed to save settings");
    } finally {
      setIsSaving(false);
    }
  };

  const handleRunTests = async () => {
    setIsRunningTests(true);
    setTestResults(null);
    try {
      const results = await runSelfTest();
      setTestResults(results);
      const passed = results.filter((r) => r.passed).length;
      toast.success(`Self-test: ${passed}/${results.length} passed`);
    } catch {
      toast.error("Failed to run self-test");
    } finally {
      setIsRunningTests(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
      </div>
    );
  }

  if (!settings) return null;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">
        Settings
      </h2>

      {/* Model Selection */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="card space-y-4"
      >
        <div className="flex items-center gap-2">
          <Cpu className="w-5 h-5 text-primary-500" />
          <h3 className="font-semibold text-slate-800 dark:text-slate-200">
            Model Configuration
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
              Light Model (Fast)
            </label>
            <input
              type="text"
              value={settings.model_light}
              onChange={(e) =>
                setSettings({ ...settings, model_light: e.target.value })
              }
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
              Heavy Model (Balanced)
            </label>
            <input
              type="text"
              value={settings.model_heavy}
              onChange={(e) =>
                setSettings({ ...settings, model_heavy: e.target.value })
              }
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
              Premium Model (Best)
            </label>
            <input
              type="text"
              value={settings.model_premium}
              onChange={(e) =>
                setSettings({ ...settings, model_premium: e.target.value })
              }
              className="input-field"
            />
          </div>
        </div>
      </motion.div>

      {/* Safety Toggles */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="card space-y-4"
      >
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-amber-500" />
          <h3 className="font-semibold text-slate-800 dark:text-slate-200">
            Safety & Approvals
          </h3>
        </div>

        <div className="space-y-3">
          <ToggleRow
            label="Require approval for destructive actions"
            description="File deletions, system modifications, etc."
            checked={settings.approval_destructive}
            onChange={(v) =>
              setSettings({ ...settings, approval_destructive: v })
            }
          />
          <ToggleRow
            label="Require approval for web browsing"
            description="Agents accessing external URLs"
            checked={settings.approval_browsing}
            onChange={(v) =>
              setSettings({ ...settings, approval_browsing: v })
            }
          />
          <ToggleRow
            label="Require approval for GUI actions"
            description="Desktop automation and screenshots"
            checked={settings.approval_gui}
            onChange={(v) => setSettings({ ...settings, approval_gui: v })}
          />
        </div>
      </motion.div>

      {/* Workspace */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="card"
      >
        <div className="flex items-center gap-2 mb-3">
          <FolderOpen className="w-5 h-5 text-emerald-500" />
          <h3 className="font-semibold text-slate-800 dark:text-slate-200">
            Workspace
          </h3>
        </div>
        <div className="flex items-center gap-3">
          <code className="flex-1 px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-lg text-sm font-mono text-slate-600 dark:text-slate-400">
            {settings.workspace_path || "/workspace"}
          </code>
        </div>
      </motion.div>

      {/* Self-Test */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="card space-y-4"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FlaskConical className="w-5 h-5 text-teal-500" />
            <h3 className="font-semibold text-slate-800 dark:text-slate-200">
              Self-Test
            </h3>
          </div>
          <button
            onClick={handleRunTests}
            disabled={isRunningTests}
            className="btn-secondary inline-flex items-center gap-2 text-sm"
          >
            {isRunningTests ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <FlaskConical className="w-4 h-4" />
            )}
            {isRunningTests ? "Running..." : "Run Tests"}
          </button>
        </div>

        {testResults && (
          <div className="space-y-2">
            {testResults.map((result) => (
              <div
                key={result.name}
                className="flex items-center justify-between py-2 px-3 rounded-lg bg-slate-50 dark:bg-slate-900/50"
              >
                <div className="flex items-center gap-2">
                  {result.passed ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-500" />
                  )}
                  <span className="text-sm text-slate-700 dark:text-slate-300">
                    {result.name}
                  </span>
                </div>
                <span className="text-xs text-slate-400 font-mono">
                  {result.duration_ms}ms
                </span>
              </div>
            ))}
          </div>
        )}
      </motion.div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="btn-primary inline-flex items-center gap-2"
        >
          {isSaving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          {isSaving ? "Saving..." : "Save Settings"}
        </button>
      </div>
    </div>
  );
}

function ToggleRow({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between py-2">
      <div>
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
          {label}
        </p>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {description}
        </p>
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={clsx(
          "relative w-11 h-6 rounded-full transition-colors duration-200",
          checked
            ? "bg-primary-500"
            : "bg-slate-300 dark:bg-slate-600"
        )}
      >
        <span
          className={clsx(
            "absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform duration-200",
            checked && "translate-x-5"
          )}
        />
      </button>
    </div>
  );
}
