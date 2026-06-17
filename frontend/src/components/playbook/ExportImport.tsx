"use client";

import { useState } from "react";
import { Download, Upload } from "lucide-react";
import { exportImportApi } from "@/lib/api";

export function ExportImport({ playbookId }: { playbookId?: string }) {
  const [importing, setImporting] = useState(false);

  const handleExport = async () => {
    if (!playbookId) return;
    const data = await exportImportApi.export(playbookId);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `playbook-${playbookId}.json`;
    a.click();
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      await exportImportApi.import(file);
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="flex gap-2">
      {playbookId && (
        <button onClick={handleExport} className="flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-800 text-gray-300 rounded hover:bg-gray-700">
          <Download className="w-3 h-3" /> Export
        </button>
      )}
      <label className="flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-800 text-gray-300 rounded hover:bg-gray-700 cursor-pointer">
        <Upload className="w-3 h-3" /> Import
        <input type="file" accept=".json" onChange={handleImport} className="hidden" />
      </label>
    </div>
  );
}
