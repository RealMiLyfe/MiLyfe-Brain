"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { playbookApi } from "@/lib/api";
import { useBrainStore } from "@/lib/store";
import { AgentAvatar } from "@/components/agents/AgentAvatar";

interface GraphNode {
  id: string;
  label: string;
  type: string;
  status: string;
  position: { x: number; y: number };
  data: Record<string, any>;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  animated: boolean;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "border-gray-600 bg-gray-800",
  running: "border-blue-500 bg-blue-500/10",
  completed: "border-green-500 bg-green-500/10",
  failed: "border-red-500 bg-red-500/10",
  cancelled: "border-yellow-500 bg-yellow-500/10",
};

export function TaskGraph() {
  const currentPlaybook = useBrainStore((s) => s.currentPlaybook);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);

  useEffect(() => {
    if (!currentPlaybook?.id) return;
    const load = async () => {
      try {
        const graph = await playbookApi.getGraph(currentPlaybook.id);
        setNodes(graph.nodes || []);
        setEdges(graph.edges || []);
      } catch {}
    };
    load();
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [currentPlaybook?.id]);

  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500 text-sm">
        No task graph available
      </div>
    );
  }

  return (
    <div className="relative w-full h-80 overflow-auto bg-gray-900/50 rounded-lg p-4">
      {/* SVG edges */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none">
        {edges.map((edge) => {
          const source = nodes.find((n) => n.id === edge.source);
          const target = nodes.find((n) => n.id === edge.target);
          if (!source || !target) return null;

          return (
            <line
              key={edge.id}
              x1={source.position.x + 75}
              y1={source.position.y + 30}
              x2={target.position.x + 75}
              y2={target.position.y}
              stroke={edge.animated ? "#6366f1" : "#4b5563"}
              strokeWidth={2}
              strokeDasharray={edge.animated ? "5,5" : undefined}
            >
              {edge.animated && (
                <animate attributeName="stroke-dashoffset" from="10" to="0" dur="1s" repeatCount="indefinite" />
              )}
            </line>
          );
        })}
      </svg>

      {/* Nodes */}
      {nodes.map((node, idx) => (
        <motion.div
          key={node.id}
          className={`absolute w-36 border rounded-lg p-2 ${STATUS_COLORS[node.status] || STATUS_COLORS.pending}`}
          style={{ left: node.position.x, top: node.position.y }}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: idx * 0.1 }}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <AgentAvatar role={node.type} size="sm" active={node.status === "running"} />
            <span className="text-[10px] text-gray-400 uppercase">{node.type}</span>
          </div>
          <p className="text-xs text-white truncate" title={node.label}>
            {node.label}
          </p>
          <div className="mt-1 flex items-center gap-1">
            <div className={`w-1.5 h-1.5 rounded-full ${
              node.status === "completed" ? "bg-green-400" :
              node.status === "running" ? "bg-blue-400 animate-pulse" :
              node.status === "failed" ? "bg-red-400" :
              "bg-gray-500"
            }`} />
            <span className="text-[10px] text-gray-500">{node.status}</span>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
