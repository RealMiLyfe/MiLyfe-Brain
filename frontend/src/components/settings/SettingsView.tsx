"use client";

import { useState, useEffect } from "react";
import { settingsApi, selfTestApi, Settings, SelfTestResult } from "@/lib/api";

export default function SettingsView() {
  const [settings, setSettings] = useState<Settings>({
    model_light: "llama3.2:3b",
    model_heavy: "llama3.1:8b",
    model_premium: "llama3.1:70b",
    safety_enabled: true,
    human_in_loop: true,
    max_concurrent_agents: 4,
    auto_approve_low_risk: false,
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [testResults, setTestResults] = useState<SelfTestResult[] | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await settingsApi.get();
        setSettings(data);
      } catch {
        // Use defaults
      }
    }
    load();
  }, []);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    try {
      const updated = await settingsApi.save(settings);
      setSettings(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      // Handle error
    } finally {
      setSaving(false);
    }
  }

  async function handleSelfTest() {
    setTesting(true);
    setTestResults(null);
    try {
      const results = await selfTestApi.run();
      setTestResults(results);
    } catch {
      setTestResults([
        {
          test_name: "Connection",
          passed: false,
          message: "Failed to run self-test. Is the backend running?",
          duration_ms: 0,
        },
      ]);
    } finally {
      setTesting(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto animate-fade-in">
      <h2 className="text-xl font-bold mb-6">Settings</h2>

      {/* Model Configuration */}
      <section className="mb-8">
        <h3 className="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wide mb-3">
          Model Configuration
        </h3>
        <div className="space-y-3">
          <div>
            <label
              htmlFor="model-light"
              className="block text-sm font-medium mb-1"
            >
              Light Model (fast tasks)
            </label>
            <input
              id="model-light"
              type="text"
              value={settings.model_light}
              onChange={(e) =>
                setSettings({ ...settings, model_light: e.target.value })
              }
              className="w-full px-4 py-2.5 rounded-lg bg-[var(--muted)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
            />
          </div>
          <div>
            <label
              htmlFor="model-heavy"
              className="block text-sm font-medium mb-1"
            >
              Heavy Model (complex reasoning)
            </label>
            <input
              id="model-heavy"
              type="text"
              value={settings.model_heavy}
              onChange={(e) =>
                setSettings({ ...settings, model_heavy: e.target.value })
              }
              className="w-full px-4 py-2.5 rounded-lg bg-[var(--muted)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
            />
          </div>
          <div>
            <label
              htmlFor="model-premium"
              className="block text-sm font-medium mb-1"
            >
              Premium Model (critical decisions)
            </label>
            <input
              id="model-premium"
              type="text"
              value={settings.model_premium}
              onChange={(e) =>
                setSettings({ ...settings, model_premium: e.target.value })
              }
              className="w-full px-4 py-2.5 rounded-lg bg-[var(--muted)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
            />
          </div>
        </div>
      </section>

      {/* Safety Settings */}
      <section className="mb-8">
        <h3 className="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wide mb-3">
          Safety & Control
        </h3>
        <div className="space-y-4">
          <label className="flex items-center justify-between p-3 rounded-lg bg-[var(--card)] border border-[var(--border)]">
            <div>
              <p className="text-sm font-medium">Safety Layer Enabled</p>
              <p className="text-xs text-[var(--muted-foreground)]">
                Validate all actions before execution
              </p>
            </div>
            <input
              type="checkbox"
              checked={settings.safety_enabled}
              onChange={(e) =>
                setSettings({ ...settings, safety_enabled: e.target.checked })
              }
              className="w-5 h-5 rounded accent-[var(--primary)]"
            />
          </label>

          <label className="flex items-center justify-between p-3 rounded-lg bg-[var(--card)] border border-[var(--border)]">
            <div>
              <p className="text-sm font-medium">Human-in-the-Loop</p>
              <p className="text-xs text-[var(--muted-foreground)]">
                Require approval for high-risk actions
              </p>
            </div>
            <input
              type="checkbox"
              checked={settings.human_in_loop}
              onChange={(e) =>
                setSettings({ ...settings, human_in_loop: e.target.checked })
              }
              className="w-5 h-5 rounded accent-[var(--primary)]"
            />
          </label>

          <label className="flex items-center justify-between p-3 rounded-lg bg-[var(--card)] border border-[var(--border)]">
            <div>
              <p className="text-sm font-medium">Auto-Approve Low Risk</p>
              <p className="text-xs text-[var(--muted-foreground)]">
                Skip approval for low-risk actions
              </p>
            </div>
            <input
              type="checkbox"
              checked={settings.auto_approve_low_risk}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  auto_approve_low_risk: e.target.checked,
                })
              }
              className="w-5 h-5 rounded accent-[var(--primary)]"
            />
          </label>
        </div>
      </section>

      {/* Save button */}
      <div className="flex items-center gap-3 mb-8">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-6 py-2.5 rounded-lg bg-[var(--primary)] text-white font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          {saving ? "Saving..." : "Save Settings"}
        </button>
        {saved && (
          <span className="text-sm text-[var(--success)] animate-fade-in">
            Settings saved!
          </span>
        )}
      </div>

      {/* Self-test */}
      <section>
        <h3 className="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wide mb-3">
          System Self-Test
        </h3>
        <button
          onClick={handleSelfTest}
          disabled={testing}
          className="px-5 py-2.5 rounded-lg border border-[var(--border)] text-sm font-medium hover:bg-[var(--muted)] disabled:opacity-50 transition-colors"
        >
          {testing ? "Running Tests..." : "Run Self-Test"}
        </button>

        {testResults && (
          <div className="mt-4 space-y-2">
            {testResults.map((result, i) => (
              <div
                key={i}
                className={`p-3 rounded-lg border ${
                  result.passed
                    ? "border-[var(--success)] border-opacity-30 bg-[var(--success)] bg-opacity-5"
                    : "border-[var(--destructive)] border-opacity-30 bg-[var(--destructive)] bg-opacity-5"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">
                    {result.passed ? "✓" : "✕"} {result.test_name}
                  </span>
                  <span className="text-xs text-[var(--muted-foreground)]">
                    {result.duration_ms}ms
                  </span>
                </div>
                <p className="text-xs text-[var(--muted-foreground)] mt-0.5">
                  {result.message}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
