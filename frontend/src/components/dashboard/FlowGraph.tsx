"use client";

import { useMemo, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeTypes,
  Position,
  MarkerType,
  Handle,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { motion } from "framer-motion";
import { clsx } from "clsx";
import type { PlaybookStep } from "@/lib/api";

// ─── Custom Node Component ──────────────────────────────────────────────────

const STATUS_STYLES: Record<string, { border: string; bg: string; ring: string }> = {
  pending: { border: "border-slate-300 dark:border-slate-600", bg: "bg-white dark:bg-slate-800", ring: "" },
  running: { border: "border-blue-400", bg: "bg-blue-50 dark:bg-blue-900/30", ring: "ring-2 ring-blue-300 dark:ring-blue-700 ring-offset-1" },
  completed: { border: "border-green-400", bg: "bg-green-50 dark:bg-green-900/30", ring: "" },
  failed: { border: "border-red-400", bg: "bg-red-50 dark:bg-red-900/30", ring: "" },
  skipped: { border: "border-slate-300 dark:border-slate-600", bg: "bg-slate-50 dark:bg-slate-800 opacity-60", ring: "" },
};

const ROLE_COLORS: Record<string, string> = {
  orchestrator: "#8b5cf6",
  researcher: "#ec4899",
  coder: "#06b6d4",
  executor: "#10b981",
  critic: "#f59e0b",
  designer: "#6366f1",
  writer: "#f97316",
  debugger: "#ef4444",
  planner: "#8b5cf6",
};

const ROLE_EMOJI: Record<string, string> = {
  orchestrator: "O",
  researcher: "R",
  coder: "C",
  executor: "E",
  critic: "Cr",
  designer: "D",
  writer: "W",
  debugger: "Db",
  planner: "P",
};

function AgentNode({ data }: { data: { label: string; status: string; role?: string; output?: string } }) {
  const styles = STATUS_STYLES[data.status] || STATUS_STYLES.pending;
  const roleColor = data.role ? ROLE_COLORS[data.role] || "#6366f1" : "#94a3b8";

  return (
    <>
      <Handle type="target" position={Position.Top} className="!w-2 !h-2 !bg-slate-400 !border-0" />
      <div
        className={clsx(
          "px-4 py-3 rounded-xl border-2 shadow-sm min-w-[160px] max-w-[220px] transition-all duration-300",
          styles.border,
          styles.bg,
          styles.ring
        )}
      >
        {/* Role badge */}
        {data.role && (
          <div className="flex items-center gap-1.5 mb-1.5">
            <div
              className="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold text-white"
              style={{ backgroundColor: roleColor }}
            >
              {ROLE_EMOJI[data.role] || "?"}
            </div>
            <span className="text-[10px] font-medium text-slate-500 dark:text-slate-400 capitalize">
              {data.role}
            </span>
          </div>
        )}

        {/* Label */}
        <p className="text-xs font-medium text-slate-700 dark:text-slate-200 leading-tight line-clamp-2">
          {data.label}
        </p>

        {/* Status indicator */}
        <div className="flex items-center gap-1.5 mt-2">
          <span
            className={clsx(
              "w-2 h-2 rounded-full",
              data.status === "completed" && "bg-green-500",
              data.status === "running" && "bg-blue-500 animate-pulse",
              data.status === "failed" && "bg-red-500",
              data.status === "pending" && "bg-slate-300 dark:bg-slate-600",
              data.status === "skipped" && "bg-slate-400"
            )}
          />
          <span className="text-[10px] text-slate-500 dark:text-slate-400 capitalize">
            {data.status}
          </span>
        </div>

        {/* Output preview */}
        {data.output && data.status === "completed" && (
          <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1.5 line-clamp-1 italic">
            {data.output.slice(0, 60)}...
          </p>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!w-2 !h-2 !bg-slate-400 !border-0" />
    </>
  );
}

const nodeTypes: NodeTypes = {
  agent: AgentNode,
};

// ─── Layout Utility ─────────────────────────────────────────────────────────

function layoutNodes(steps: PlaybookStep[]): { nodes: Node[]; edges: Edge[] } {
  if (!steps || steps.length === 0) return { nodes: [], edges: [] };

  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const COL_WIDTH = 260;
  const ROW_HEIGHT = 120;

  // Simple layered layout: place nodes in a grid
  // For now, simple sequential with some parallelism
  const cols = Math.min(3, Math.ceil(Math.sqrt(steps.length)));

  steps.forEach((step, idx) => {
    const col = idx % cols;
    const row = Math.floor(idx / cols);

    nodes.push({
      id: step.id,
      type: "agent",
      position: { x: col * COL_WIDTH + 50, y: row * ROW_HEIGHT + 50 },
      data: {
        label: step.name || `Step ${idx + 1}`,
        status: step.status,
        role: step.agent_role,
        output: step.output,
      },
    });

    // Create edge to previous step (simple sequential for now)
    if (idx > 0) {
      edges.push({
        id: `e-${steps[idx - 1].id}-${step.id}`,
        source: steps[idx - 1].id,
        target: step.id,
        animated: step.status === "running",
        style: {
          stroke: step.status === "completed" ? "#10b981" : step.status === "running" ? "#3b82f6" : "#94a3b8",
          strokeWidth: 2,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: step.status === "completed" ? "#10b981" : "#94a3b8",
        },
      });
    }
  });

  return { nodes, edges };
}

// ─── Main Component ─────────────────────────────────────────────────────────

interface FlowGraphProps {
  steps: PlaybookStep[];
}

export function FlowGraph({ steps }: FlowGraphProps) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => layoutNodes(steps),
    [steps]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Update nodes when steps change
  useMemo(() => {
    const { nodes: newNodes, edges: newEdges } = layoutNodes(steps);
    setNodes(newNodes);
    setEdges(newEdges);
  }, [steps, setNodes, setEdges]);

  if (!steps || steps.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-sm text-slate-400 dark:text-slate-500">
        No steps to visualize. Create a playbook to see the task graph.
      </div>
    );
  }

  const completedCount = steps.filter((s) => s.status === "completed").length;
  const percentage = Math.round((completedCount / steps.length) * 100);

  return (
    <div className="space-y-3">
      {/* Progress summary */}
      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>{completedCount}/{steps.length} steps complete</span>
        <span className="font-mono">{percentage}%</span>
      </div>
      <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-primary-500 to-green-400 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>

      {/* React Flow Canvas */}
      <div className="h-[400px] w-full rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden bg-slate-50 dark:bg-slate-900/50">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          proOptions={{ hideAttribution: true }}
          className="!bg-transparent"
        >
          <Background color="#94a3b8" gap={20} size={1} />
          <Controls className="!bg-white dark:!bg-slate-800 !border-slate-200 dark:!border-slate-700 !shadow-sm" />
          <MiniMap
            className="!bg-white dark:!bg-slate-800 !border-slate-200 dark:!border-slate-700"
            nodeColor={(node) => {
              const status = (node.data as { status?: string })?.status;
              if (status === "completed") return "#10b981";
              if (status === "running") return "#3b82f6";
              if (status === "failed") return "#ef4444";
              return "#94a3b8";
            }}
          />
        </ReactFlow>
      </div>
    </div>
  );
}
