"use client";

import { useEffect, useState } from "react";
import { File, Folder, RefreshCw } from "lucide-react";
import { workspaceApi } from "@/lib/api";

export function WorkspaceFiles() {
  const [files, setFiles] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await workspaceApi.recent();
      setFiles(data.files || []);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  return (
    <div>
      <div className="flex justify-end mb-2">
        <button onClick={load} className="p-1 text-gray-500 hover:text-white">
          <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>
      <div className="h-56 overflow-y-auto space-y-1">
        {files.length === 0 ? (
          <p className="text-gray-600 text-center py-8 text-sm">No files yet</p>
        ) : (
          files.map((file, i) => (
            <div key={i} className="flex items-center gap-2 px-2 py-1 rounded hover:bg-gray-800">
              <File className="w-3 h-3 text-gray-500" />
              <span className="text-xs text-gray-300 truncate">{file.path}</span>
              <span className="text-xs text-gray-600 ml-auto">{(file.size / 1024).toFixed(1)}KB</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
