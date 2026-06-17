"use client";

import { useEffect, useState } from "react";
import { settingsApi, selfTestApi } from "@/lib/api";

export default function SettingsView() {
  const [settings, setSettings] = useState<any>({});
  const [testResults, setTestResults] = useState<any>(null);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    settingsApi.get().then(setSettings).catch(() => {});
  }, []);

  const saveSettings = async () => {
    setSaving(true);
    try { await settingsApi.save(settings); } catch {}
    setSaving(false);
  };

  const runSelfTest = async () => {
    setTesting(true);
    try { const r = await selfTestApi.run(); setTestResults(r); } catch {}
    setTesting(false);
  };

  return (
    <div className="max-w-3xl animate-fadeIn">
      <h2 className="text-xl font-bold mb-6">Settings</h2>

      {/* Model Settings */}
      <Section title="Models">
        <Field label="Light Model" value={settings.light_model || ""} onChange={(v) => setSettings({ ...settings, light_model: v })} />
        <Field label="Heavy Model" value={settings.heavy_model || ""} onChange={(v) => setSettings({ ...settings, heavy_model: v })} />
        <Field label="Premium Model" value={settings.premium_model || ""} onChange={(v) => setSettings({ ...settings, premium_model: v })} />
      </Section>

      {/* Safety */}
      <Section title="Safety & Approvals">
        <Toggle label="Require approval for destructive actions" checked={settings.require_approval_destructive ?? true} onChange={(v) => setSettings({ ...settings, require_approval_destructive: v })} />
        <Toggle label="Require approval for web browsing" checked={settings.require_approval_browsing ?? true} onChange={(v) => setSettings({ ...settings, require_approval_browsing: v })} />
        <Toggle label="Require approval for GUI actions" checked={settings.require_approval_gui ?? true} onChange={(v) => setSettings({ ...settings, require_approval_gui: v })} />
        <Toggle label="Auto git snapshots" checked={settings.auto_git_snapshots ?? true} onChange={(v) => setSettings({ ...settings, auto_git_snapshots: v })} />
      </Section>

      <button onClick={saveSettings} disabled={saving} className="mt-4 px-6 py-2 bg-[var(--primary)] text-white rounded-lg hover:opacity-90 disabled:opacity-50">
        {saving ? "Saving..." : "Save Settings"}
      </button>

      {/* Self-Test */}
      <div className="mt-10 border-t border-[var(--border)] pt-6">
        <h3 className="font-medium mb-3">System Self-Test</h3>
        <button onClick={runSelfTest} disabled={testing} className="px-4 py-2 bg-[var(--card)] border border-[var(--border)] rounded-lg hover:border-[var(--primary)]/50 disabled:opacity-50">
          {testing ? "Testing..." : "Run Self-Test"}
        </button>
        {testResults && (
          <div className="mt-4 space-y-2">
            {testResults.results?.map((r: any, i: number) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <span className={r.status === "pass" ? "text-green-400" : r.status === "skip" ? "text-yellow-400" : "text-red-400"}>
                  {r.status === "pass" ? "PASS" : r.status === "skip" ? "SKIP" : "FAIL"}
                </span>
                <span>{r.service}</span>
                <span className="text-[var(--muted-foreground)]">{r.message}</span>
                <span className="text-xs text-[var(--muted-foreground)]">{r.latency_ms?.toFixed(0)}ms</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-6">
      <h3 className="font-medium text-sm text-[var(--muted-foreground)] mb-3">{title}</h3>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center justify-between">
      <label className="text-sm">{label}</label>
      <input type="text" value={value} onChange={(e) => onChange(e.target.value)} className="px-3 py-1.5 bg-[var(--background)] border border-[var(--border)] rounded text-sm w-48 text-[var(--foreground)]" />
    </div>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between">
      <label className="text-sm">{label}</label>
      <button onClick={() => onChange(!checked)} className={`w-10 h-5 rounded-full transition-colors ${checked ? "bg-[var(--primary)]" : "bg-[var(--muted)]"}`}>
        <div className={`w-4 h-4 rounded-full bg-white transition-transform ${checked ? "translate-x-5" : "translate-x-0.5"}`} />
      </button>
    </div>
  );
}
