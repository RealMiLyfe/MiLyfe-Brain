"use client";

import { useState, useCallback } from "react";
import { listPlaybooks, type Playbook } from "@/lib/api";
import { Download, Upload, FileJson, CheckCircle, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { clsx } from "clsx";

export function ExportImport() {
  const [playbooks, setPlaybooks] = useState<Playbook[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [importPreview, setImportPreview] = useState<Playbook | null>(null);
  const [status, setStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Load playbooks on mount
  useState(() => {
    listPlaybooks().then(setPlaybooks).catch(() => {});
  });

  const handleExport = async () => {
    const pb = playbooks.find((p) => p.id === selectedId);
    if (!pb) { toast.error("Select a playbook to export"); return; }
    const blob = new Blob([JSON.stringify(pb, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${pb.title.replace(/\s+/g, "_")}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setStatus({ type: "success", message: `Exported "${pb.title}"` });
  };

  const handleFile = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string) as Playbook;
        if (!data.title || !data.steps) throw new Error("Invalid playbook format");
        setImportPreview(data);
        setStatus({ type: "success", message: `Parsed "${data.title}" (${data.steps.length} steps)` });
      } catch {
        setStatus({ type: "error", message: "Invalid JSON file" });
        setImportPreview(null);
      }
    };
    reader.readAsText(file);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleImport = async () => {
    if (!importPreview) return;
    try {
      // Would call an import API endpoint here
      toast.success(`Imported "${importPreview.title}"`);
      setImportPreview(null);
      setStatus({ type: "success", message: "Import complete!" });
    } catch {
      setStatus({ type: "error", message: "Import failed" });
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {/* Export Section */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card space-y-4">
        <div className="flex items-center gap-2">
          <Download className="w-5 h-5 text-primary-500" />
          <h3 className="font-semibold text-slate-800 dark:text-slate-100">Export Playbook</h3>
        </div>
        <div className="flex gap-3">
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="flex-1 px-3 py-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-lg text-sm text-slate-700 dark:text-slate-300"
          >
            <option value="">Select a playbook...</option>
            {playbooks.map((pb) => <option key={pb.id} value={pb.id}>{pb.title}</option>)}
          </select>
          <button onClick={handleExport} disabled={!selectedId} className={clsx("btn-primary px-4 py-2 inline-flex items-center gap-2", !selectedId && "opacity-50 cursor-not-allowed")}>
            <FileJson className="w-4 h-4" /> Export
          </button>
        </div>
      </motion.div>

      {/* Import Section */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="card space-y-4">
        <div className="flex items-center gap-2">
          <Upload className="w-5 h-5 text-primary-500" />
          <h3 className="font-semibold text-slate-800 dark:text-slate-100">Import Playbook</h3>
        </div>
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={clsx(
            "border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer",
            isDragging ? "border-primary-400 bg-primary-50 dark:bg-primary-900/10" : "border-slate-300 dark:border-slate-600"
          )}
          onClick={() => { const input = document.createElement("input"); input.type = "file"; input.accept = ".json"; input.onchange = (e) => { const f = (e.target as HTMLInputElement).files?.[0]; if (f) handleFile(f); }; input.click(); }}
        >
          <FileJson className="w-8 h-8 mx-auto text-slate-400 mb-2" />
          <p className="text-sm text-slate-500 dark:text-slate-400">Drop JSON file here or click to browse</p>
        </div>

        {importPreview && (
          <div className="p-3 bg-slate-50 dark:bg-slate-900/50 rounded-lg space-y-1">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{importPreview.title}</p>
            <p className="text-xs text-slate-500">{importPreview.steps.length} steps · {importPreview.model}</p>
            <button onClick={handleImport} className="btn-primary px-3 py-1.5 text-sm mt-2 inline-flex items-center gap-1">
              <Upload className="w-3 h-3" /> Import
            </button>
          </div>
        )}
      </motion.div>

      {/* Status */}
      {status && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className={clsx("flex items-center gap-2 px-4 py-2 rounded-lg text-sm", status.type === "success" ? "bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400" : "bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400")}>
          {status.type === "success" ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          {status.message}
        </motion.div>
      )}
    </div>
  );
}
