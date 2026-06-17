"use client";

import { useState, useRef } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8200";

export default function ExportImport() {
  const [importing, setImporting] = useState(false);
  const [message, setMessage] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const handleExport = async (playbookId: string) => {
    try {
      const res = await fetch(`${API_URL}/api/playbooks/io/export/${playbookId}`, { method: "POST" });
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `playbook_${playbookId.slice(0, 8)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setMessage("Exported successfully!");
    } catch { setMessage("Export failed"); }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      const res = await fetch(`${API_URL}/api/playbooks/io/import`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
      });
      if (res.ok) { setMessage("Imported successfully!"); }
      else { setMessage("Import failed"); }
    } catch { setMessage("Invalid file"); }
    setImporting(false);
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <div className="flex items-center gap-3">
      <button onClick={() => fileRef.current?.click()} disabled={importing} className="px-3 py-1.5 text-xs border border-[var(--border)] rounded-lg hover:border-[var(--primary)]/50">
        {importing ? "Importing..." : "Import Playbook"}
      </button>
      <input ref={fileRef} type="file" accept=".json" onChange={handleImport} className="hidden" />
      {message && <span className="text-xs text-[var(--muted-foreground)]">{message}</span>}
    </div>
  );
}
