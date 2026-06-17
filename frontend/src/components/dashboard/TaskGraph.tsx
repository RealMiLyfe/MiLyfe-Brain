"use client";

import { useEffect, useState } from "react";
import { playbookApi } from "@/lib/api";
import { useBrainStore } from "@/lib/store";

interface GraphNode { id: string; label: string; type: string; status: string; position: { x: number; y: number }; }
interface GraphEdge { id: string; source: string; target: string; animated: boolean; }

export default function TaskGraph() {
  const { currentPlaybook } = useBrainStore();
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);

  useEffect(() => {
    if (!currentPlaybook) return;
    const load = async () => {
      try {
        const graph = await playbookApi.getGraph(currentPlaybook.id) as any;
        setNodes(graph.nodes || []);
        setEdges(graph.edges || []);
      } catch {}
    };
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [currentPlaybook]);

  if (!nodes.length) {
    return <div className="text-sm text-[var(--muted-foreground)] text-center py-8">No task graph available</div>;
  }

  const statusColors: Record<string, string> = {
    pending: "#52525b",
    running: "#3b82f6",
    completed: "#10b981",
    failed: "#ef4444",
    cancelled: "#6b7280",
  };

  // Calculate SVG bounds
  const maxX = Math.max(...nodes.map((n) => n.position.x)) + 200;
  const maxY = Math.max(...nodes.map((n) => n.position.y)) + 100;

  return (
    <div className="bg-[var(--card)] border border-[var(--border)] rounded-lg p-4 overflow-auto">
      <h3 className="text-sm font-medium mb-3">Task Dependency Graph</h3>
      <svg width={Math.max(maxX, 400)} height={Math.max(maxY, 200)} className="w-full" viewBox={`0 0 ${Math.max(maxX, 400)} ${Math.max(maxY, 200)}`}>
        {/* Edges */}
        {edges.map((edge) => {
          const source = nodes.find((n) => n.id === edge.source);
          const target = nodes.find((n) => n.id === edge.target);
          if (!source || !target) return null;
          return (
            <line
              key={edge.id}
              x1={source.position.x + 75}
              y1={source.position.y + 20}
              x2={target.position.x + 75}
              y2={target.position.y + 20}
              stroke={edge.animated ? "#3b82f6" : "#52525b"}
              strokeWidth={edge.animated ? 2 : 1}
              strokeDasharray={edge.animated ? "5,5" : undefined}
              markerEnd="url(#arrowhead)"
            />
          );
        })}

        {/* Arrow marker */}
        <defs>
          <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="#52525b" />
          </marker>
        </defs>

        {/* Nodes */}
        {nodes.map((node) => (
          <g key={node.id} transform={`translate(${node.position.x}, ${node.position.y})`}>
            <rect
              width={150}
              height={40}
              rx={6}
              fill={statusColors[node.status] || "#52525b"}
              fillOpacity={0.15}
              stroke={statusColors[node.status] || "#52525b"}
              strokeWidth={node.status === "running" ? 2 : 1}
            />
            <text x={75} y={16} textAnchor="middle" fill="#e4e4e7" fontSize={10} fontWeight="bold">
              {node.label.slice(0, 20)}
            </text>
            <text x={75} y={30} textAnchor="middle" fill="#a1a1aa" fontSize={9}>
              {node.type} • {node.status}
            </text>
            {node.status === "running" && (
              <circle cx={140} cy={8} r={4} fill="#3b82f6">
                <animate attributeName="opacity" values="1;0.3;1" dur="1.5s" repeatCount="indefinite" />
              </circle>
            )}
          </g>
        ))}
      </svg>
    </div>
  );
}
