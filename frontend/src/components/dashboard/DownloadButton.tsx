"use client";

import { Download } from "lucide-react";
import { downloadApi } from "@/lib/api";

export function DownloadButton() {
  return (
    <a
      href={downloadApi.workspace()}
      download
      className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-800 text-gray-300 rounded-lg hover:bg-gray-700 transition-colors"
    >
      <Download className="w-4 h-4" />
      Download Workspace
    </a>
  );
}
