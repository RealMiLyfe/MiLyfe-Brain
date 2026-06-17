"use client";

import { useState, useEffect } from "react";
import { Save, Play, CheckCircle, XCircle } from "lucide-react";
import { settingsApi, selfTestApi, healthApi } from "@/lib/api";

export function SettingsView() {
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [health, setHealth] = useState<any>(null);
  const [testResults, setTestResults] = useState<any>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const s = await settingsApi.get();
        setSettings(s.settings || {});
        const h = await healthApi.check();
        setHealth(h);
      } catch {}
    };
    load();
  }, []);

  const save = async () => {
    await settingsApi.save(settings);
  };

  const runSelfTest = async () => {
    setTesting(true);
    try { setTestResults(await selfTestApi.run()); } catch {}
    setTesting(false);
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-2xl font-bold text-white mb-6">Settings</h1>

      {/* Health */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-6">
        <h2 className="text-lg font-semibold text-white mb-3">Service Health</h2>
        {health ? (
          <div className="grid grid-cols-3 gap-4">
            {Object.entries(health.services || {}).map(([name, status]) => (
              <div key={name} className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${status === "connected" ? "bg-green-400" : "bg-red-400"}`} />
                <span className="text-sm text-gray-300 capitalize">{name}</span>
                <span className="text-xs text-gray-500 ml-auto">{status as string}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-sm">Loading...</p>
        )}
      </div>

      {/* Self-Test */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-6">
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-lg font-semibold text-white">Self-Test</h2>
          <button onClick={runSelfTest} disabled={testing} className="flex items-center gap-1 px-3 py-1.5 bg-brain-600 text-white rounded text-sm hover:bg-brain-700 disabled:opacity-50">
            <Play className="w-3 h-3" /> {testing ? "Running..." : "Run Tests"}
          </button>
        </div>
        {testResults && (
          <div className="space-y-2">
            {testResults.tests?.map((t: any) => (
              <div key={t.test_name} className="flex items-center gap-2">
                {t.passed ? <CheckCircle className="w-4 h-4 text-green-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
                <span className="text-sm text-gray-300">{t.test_name}</span>
                <span className="text-xs text-gray-500 ml-auto">{t.duration_ms.toFixed(0)}ms</span>
              </div>
            ))}
            <p className={`text-sm mt-2 ${testResults.overall ? "text-green-400" : "text-red-400"}`}>
              {testResults.overall ? "All tests passed" : "Some tests failed"} ({testResults.duration_ms.toFixed(0)}ms)
            </p>
          </div>
        )}
      </div>

      {/* Settings Form */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-lg font-semibold text-white">Runtime Settings</h2>
          <button onClick={save} className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700">
            <Save className="w-3 h-3" /> Save
          </button>
        </div>
        <div className="space-y-3">
          {[
            { key: "default_model", label: "Default Model", placeholder: "llama3.1:8b" },
            { key: "max_agents", label: "Max Agents", placeholder: "10" },
            { key: "output_style", label: "Output Style", placeholder: "default" },
          ].map((field) => (
            <div key={field.key} className="flex items-center gap-3">
              <label className="text-sm text-gray-400 w-40">{field.label}</label>
              <input
                type="text"
                value={settings[field.key] || ""}
                onChange={(e) => setSettings({ ...settings, [field.key]: e.target.value })}
                placeholder={field.placeholder}
                className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-brain-500"
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
