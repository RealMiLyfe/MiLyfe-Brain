"use client";

import { useState, useEffect } from "react";
import { getWorkspaceTree, type WorkspaceNode } from "@/lib/api";
import {
  Folder,
  File,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  X,
  FileCode,
  FileText,
  Image,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx } from "clsx";

export function WorkspaceFiles() {
  const [tree, setTree] = useState<WorkspaceNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<WorkspaceNode | null>(null);

  const fetchTree = async () => {
    setLoading(true);
    try {
      const data = await getWorkspaceTree();
      setTree(data);
    } catch { /* silently fail */ }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchTree(); }, []);

  return (
    <div className="card flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Folder className="w-4 h-4 text-primary-500" />
          <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-200">
            Workspace Files
          </h3>
        </div>
        <button
          onClick={fetchTree}
          disabled={loading}
          className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        >
          <RefreshCw className={clsx("w-3.5 h-3.5 text-slate-400", loading && "animate-spin")} />
        </button>
      </div>


      <div className="flex-1 overflow-y-auto max-h-72 scrollbar-thin">
        {tree.length > 0 ? (
          <div className="space-y-0.5">
            {tree.map((node) => (
              <TreeNode key={node.path} node={node} depth={0} onSelect={setSelectedFile} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-400 dark:text-slate-500 py-8 text-center">
            {loading ? "Loading..." : "No workspace files"}
          </p>
        )}
      </div>

      {/* File Preview Modal */}
      <AnimatePresence>
        {selectedFile && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
            onClick={() => setSelectedFile(null)}
          >
            <motion.div
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.95 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white dark:bg-slate-800 rounded-xl shadow-xl max-w-lg w-full p-4"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{selectedFile.name}</span>
                <button onClick={() => setSelectedFile(null)} className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700">
                  <X className="w-4 h-4 text-slate-400" />
                </button>
              </div>
              <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-3 text-xs font-mono text-slate-600 dark:text-slate-400 max-h-64 overflow-auto">
                <p>Path: {selectedFile.path}</p>
                {selectedFile.size && <p>Size: {(selectedFile.size / 1024).toFixed(1)} KB</p>}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}


function getFileIcon(name: string) {
  const ext = name.split(".").pop()?.toLowerCase();
  if (["ts", "tsx", "js", "jsx", "py", "rs"].includes(ext || "")) return FileCode;
  if (["md", "txt", "json", "yaml", "yml"].includes(ext || "")) return FileText;
  if (["png", "jpg", "jpeg", "svg", "gif"].includes(ext || "")) return Image;
  return File;
}

function TreeNode({ node, depth, onSelect }: { node: WorkspaceNode; depth: number; onSelect: (n: WorkspaceNode) => void }) {
  const [expanded, setExpanded] = useState(depth < 1);
  const isDir = node.type === "directory";
  const Icon = isDir ? Folder : getFileIcon(node.name);

  return (
    <div>
      <button
        onClick={() => isDir ? setExpanded(!expanded) : onSelect(node)}
        className="w-full flex items-center gap-1.5 py-1 px-1 rounded text-xs hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors"
        style={{ paddingLeft: `${depth * 12 + 4}px` }}
      >
        {isDir ? (
          expanded ? <ChevronDown className="w-3 h-3 text-slate-400" /> : <ChevronRight className="w-3 h-3 text-slate-400" />
        ) : <span className="w-3" />}
        <Icon className={clsx("w-3.5 h-3.5", isDir ? "text-amber-500" : "text-slate-400")} />
        <span className="text-slate-700 dark:text-slate-300 truncate">{node.name}</span>
      </button>
      {isDir && expanded && node.children && (
        <div>{node.children.map((c) => <TreeNode key={c.path} node={c} depth={depth + 1} onSelect={onSelect} />)}</div>
      )}
    </div>
  );
}
