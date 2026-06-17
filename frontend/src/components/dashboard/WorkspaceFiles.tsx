"use client";

import { useEffect, useState } from "react";
import { workspaceApi } from "@/lib/api";

interface FileNode { name: string; path: string; is_dir: boolean; size: number; children?: FileNode[]; }

export default function WorkspaceFiles() {
  const [tree, setTree] = useState<FileNode[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await workspaceApi.tree() as any;
        setTree(data.tree || []);
      } catch {}
      setLoading(false);
    };
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="text-xs text-[var(--muted-foreground)]">Loading workspace...</div>;

  return (
    <div className="bg-[var(--card)] border border-[var(--border)] rounded-lg">
      <div className="p-3 border-b border-[var(--border)]">
        <h3 className="text-sm font-medium">Workspace Files</h3>
      </div>
      <div className="max-h-64 overflow-auto p-2">
        {tree.length === 0 ? (
          <p className="text-xs text-[var(--muted-foreground)] p-2">Workspace empty</p>
        ) : (
          <FileTree nodes={tree} depth={0} />
        )}
      </div>
    </div>
  );
}

function FileTree({ nodes, depth }: { nodes: FileNode[]; depth: number }) {
  return (
    <ul className="space-y-0.5" role="tree">
      {nodes.map((node) => (
        <li key={node.path} role="treeitem" style={{ paddingLeft: `${depth * 12}px` }}>
          <div className="flex items-center gap-1.5 py-0.5 px-1 rounded hover:bg-[var(--muted)]/30 text-xs">
            <span className="text-[var(--muted-foreground)]">{node.is_dir ? "D" : "F"}</span>
            <span className={node.is_dir ? "font-medium" : ""}>{node.name}</span>
            {!node.is_dir && node.size > 0 && (
              <span className="text-[var(--muted-foreground)] ml-auto">{formatSize(node.size)}</span>
            )}
          </div>
          {node.is_dir && node.children && node.children.length > 0 && (
            <FileTree nodes={node.children} depth={depth + 1} />
          )}
        </li>
      ))}
    </ul>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}
