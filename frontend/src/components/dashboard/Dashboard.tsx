"use client";

import { useEffect, useState, useCallback } from "react";
import { useStore } from "@/lib/store";
import { usePlaybookStatus } from "@/hooks/usePlaybookStatus";
import {
  listActiveAgents,
  getWorkspaceTree,
  downloadWorkspace,
  type Agent,
  type WorkspaceNode,
  type StreamEvent,
} from "@/lib/api";
import { AgentAvatar } from "@/components/agents/AgentAvatar";
import {
  Download,
  Folder,
  File,
  ChevronRight,
  ChevronDown,
  Activity,
  Wifi,
  WifiOff,
  Zap,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx } from "clsx";
import { toast } from "sonner";

export function Dashboard() {
  const currentPlaybook = useStore((state) => state.currentPlaybook);
  const agents = useStore((state) => state.agents);
  const setAgents = useStore((state) => state.setAgents);
  const events = useStore((state) => state.events);
  const isConnected = useStore((state) => state.isConnected);
  const [workspace, setWorkspace] = useState<WorkspaceNode[]>([]);
  const [isLoadingWorkspace, setIsLoadingWorkspace] = useState(false);

  const { status, progress, currentStep, steps } = usePlaybookStatus(
    currentPlaybook?.id || null
  );

  // Poll for agents
  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const agentList = await listActiveAgents();
        setAgents(agentList);
      } catch {
        // Silently fail - will retry
      }
    };

    fetchAgents();
    const interval = setInterval(fetchAgents, 5000);
    return () => clearInterval(interval);
  }, [setAgents]);

  // Fetch workspace tree
  useEffect(() => {
    const fetchWorkspace = async () => {
      setIsLoadingWorkspace(true);
      try {
        const tree = await getWorkspaceTree();
        setWorkspace(tree);
      } catch {
        // Workspace may not be available yet
      } finally {
        setIsLoadingWorkspace(false);
      }
    };

    fetchWorkspace();
    const interval = setInterval(fetchWorkspace, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleDownload = async () => {
    try {
      const blob = await downloadWorkspace();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "workspace.zip";
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Workspace downloaded!");
    } catch {
      toast.error("Failed to download workspace");
    }
  };

  const agentList = Array.from(agents.values());

  return (
    <div className="space-y-6">
      {/* Connection Status */}
      <div className="flex items-center gap-2">
        {isConnected ? (
          <Wifi className="w-4 h-4 text-green-500" />
        ) : (
          <WifiOff className="w-4 h-4 text-red-400" />
        )}
        <span className="text-xs text-slate-500 dark:text-slate-400">
          {isConnected ? "Connected" : "Disconnected"}
        </span>
      </div>

      {/* Playbook Progress */}
      {currentPlaybook && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="card"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-primary-500" />
              <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-200">
                Playbook Progress
              </h3>
            </div>
            <span
              className={clsx(
                "text-xs px-2 py-0.5 rounded-full font-medium",
                status === "running" &&
                  "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400",
                status === "completed" &&
                  "bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400",
                status === "failed" &&
                  "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400",
                status === "paused" &&
                  "bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400"
              )}
            >
              {status}
            </span>
          </div>

          {/* Progress bar */}
          <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-primary-500 to-primary-400 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
          <div className="flex justify-between mt-2">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {currentStep || "Waiting..."}
            </span>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {progress}%
            </span>
          </div>

          {/* Steps */}
          {steps.length > 0 && (
            <div className="mt-4 space-y-2">
              {steps.map((step) => (
                <div
                  key={step.id}
                  className="flex items-center gap-2 text-xs"
                >
                  <span
                    className={clsx(
                      "w-2 h-2 rounded-full",
                      step.status === "completed" && "bg-green-500",
                      step.status === "running" && "bg-blue-500 animate-pulse",
                      step.status === "failed" && "bg-red-500",
                      step.status === "pending" && "bg-slate-300 dark:bg-slate-600",
                      step.status === "skipped" && "bg-slate-400"
                    )}
                  />
                  <span className="text-slate-600 dark:text-slate-400">
                    {step.name}
                  </span>
                  {step.agent_role && (
                    <span className="text-slate-400 dark:text-slate-500">
                      ({step.agent_role})
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </motion.div>
      )}

      {/* Agents Grid */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-200">
            Active Agents
          </h3>
          <span className="text-xs text-slate-400">
            {agentList.length} agent{agentList.length !== 1 ? "s" : ""}
          </span>
        </div>
        {agentList.length > 0 ? (
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-4">
            <AnimatePresence>
              {agentList.map((agent) => (
                <motion.div
                  key={agent.id}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="flex flex-col items-center gap-1 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors cursor-default"
                  title={`${agent.name} - ${agent.current_task || "Idle"}`}
                >
                  <AgentAvatar
                    role={agent.role}
                    name={agent.name}
                    status={agent.status}
                    showLabel
                  />
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        ) : (
          <div className="text-center py-8 text-sm text-slate-400 dark:text-slate-500">
            No active agents. Create a playbook to spawn agents.
          </div>
        )}
      </div>

      {/* Bottom grid: Events + Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Live Event Log */}
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <Activity className="w-4 h-4 text-primary-500" />
            <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-200">
              Live Events
            </h3>
          </div>
          <div className="space-y-2 max-h-64 overflow-y-auto scrollbar-thin">
            {events.length > 0 ? (
              events
                .slice()
                .reverse()
                .map((event) => (
                  <EventRow key={event.id} event={event} />
                ))
            ) : (
              <p className="text-sm text-slate-400 dark:text-slate-500 py-4 text-center">
                No events yet
              </p>
            )}
          </div>
        </div>

        {/* Workspace Tree */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Folder className="w-4 h-4 text-primary-500" />
              <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-200">
                Workspace
              </h3>
            </div>
            <button
              onClick={handleDownload}
              className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              title="Download workspace"
            >
              <Download className="w-4 h-4 text-slate-500" />
            </button>
          </div>
          <div className="max-h-64 overflow-y-auto scrollbar-thin">
            {workspace.length > 0 ? (
              <div className="space-y-0.5">
                {workspace.map((node) => (
                  <FileTreeNode key={node.path} node={node} depth={0} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-400 dark:text-slate-500 py-4 text-center">
                {isLoadingWorkspace ? "Loading..." : "No workspace files"}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function EventRow({ event }: { event: StreamEvent }) {
  return (
    <div className="flex items-start gap-2 py-1.5 px-2 rounded text-xs hover:bg-slate-50 dark:hover:bg-slate-700/30">
      <span className="text-slate-400 dark:text-slate-500 font-mono whitespace-nowrap">
        {new Date(event.timestamp).toLocaleTimeString()}
      </span>
      {event.agent_role && (
        <span className="text-primary-500 font-medium capitalize flex-shrink-0">
          [{event.agent_role}]
        </span>
      )}
      <span className="text-slate-600 dark:text-slate-300 break-all">
        {event.content}
      </span>
    </div>
  );
}

function FileTreeNode({
  node,
  depth,
}: {
  node: WorkspaceNode;
  depth: number;
}) {
  const [expanded, setExpanded] = useState(depth < 1);

  const isDir = node.type === "directory";

  return (
    <div>
      <button
        onClick={() => isDir && setExpanded(!expanded)}
        className={clsx(
          "w-full flex items-center gap-1.5 py-1 px-1 rounded text-xs hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors",
          !isDir && "cursor-default"
        )}
        style={{ paddingLeft: `${depth * 12 + 4}px` }}
      >
        {isDir ? (
          expanded ? (
            <ChevronDown className="w-3 h-3 text-slate-400" />
          ) : (
            <ChevronRight className="w-3 h-3 text-slate-400" />
          )
        ) : (
          <span className="w-3" />
        )}
        {isDir ? (
          <Folder className="w-3.5 h-3.5 text-amber-500" />
        ) : (
          <File className="w-3.5 h-3.5 text-slate-400" />
        )}
        <span className="text-slate-700 dark:text-slate-300 truncate">
          {node.name}
        </span>
      </button>
      {isDir && expanded && node.children && (
        <div>
          {node.children.map((child) => (
            <FileTreeNode key={child.path} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
