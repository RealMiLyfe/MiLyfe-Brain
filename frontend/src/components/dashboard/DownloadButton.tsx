"use client";

import { useState } from "react";
import { downloadWorkspace } from "@/lib/api";
import { Download, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { clsx } from "clsx";

export function DownloadButton() {
  const [loading, setLoading] = useState(false);

  const handleDownload = async () => {
    setLoading(true);
    try {
      const blob = await downloadWorkspace();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `workspace-${Date.now()}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("Workspace downloaded!");
    } catch {
      toast.error("Failed to download workspace");
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleDownload}
      disabled={loading}
      className={clsx(
        "inline-flex items-center gap-2 px-4 py-2 rounded-lg",
        "bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700",
        "text-sm font-medium text-slate-700 dark:text-slate-300",
        "hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors",
        loading && "opacity-60 cursor-not-allowed"
      )}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <Download className="w-4 h-4" />
      )}
      {loading ? "Downloading..." : "Download Workspace"}
    </button>
  );
}
