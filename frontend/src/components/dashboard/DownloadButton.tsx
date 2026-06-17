"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8200";

export default function DownloadButton() {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const res = await fetch(`${API_URL}/api/download/workspace`);
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "workspace.zip";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Download error:", e);
    }
    setDownloading(false);
  };

  return (
    <button
      onClick={handleDownload}
      disabled={downloading}
      className="px-3 py-1.5 text-xs bg-[var(--card)] border border-[var(--border)] rounded-lg hover:border-[var(--primary)]/50 disabled:opacity-50"
      aria-label="Download workspace as zip"
    >
      {downloading ? "Downloading..." : "Download Workspace"}
    </button>
  );
}
