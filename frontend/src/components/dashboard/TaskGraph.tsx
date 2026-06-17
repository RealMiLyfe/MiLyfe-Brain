"use client";

import { useState, useEffect } from "react";
import { playbookApi, PlaybookGraphResponse } from "@/lib/api";

const STATUS_NODE_COLORS: Record<string, string> = {
  pending: "#a1a1aa",
  running: "#5c7cfa",
  completed: "#10b981",
  failed: "#ef4444",
  skipped: "#6b7280",
};

interface TaskGraphProps {
  playbookId: string;
}

export default function TaskGraph({ playbookId }: TaskGraphProps) {
  const [graph, setGraph] = useState<PlaybookGraphResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadGraph() {
      try {
        const data = await playbookApi.getGraph(playbookId);
        if (!cancelled) setGraph(data);
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Failed to load graph");
      }
    }

    loadGraph();
    const interval = setInterval(loadGraph, 5000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [playbookId]);

  if (error) {
    return (
      <div className="text-sm text-[var(--muted-foreground)] text-center py-8">
        {error}
      </div>
    );
  }

  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="text-sm text-[var(--muted-foreground)] text-center py-8">
        Loading task graph...
      </div>
    );
  }

  const svgWidth = 600;
  const svgHeight = Math.max(200, graph.nodes.length * 60);
  const nodeRadius = 20;

  // Auto-layout: place nodes in a vertical DAG
  const nodePositions = graph.nodes.map((node, i) => ({
    ...node,
    cx: node.x || 100 + (i % 3) * 200,
    cy: node.y || 60 + Math.floor(i / 3) * 80,
  }));

  return (
    <div className="overflow-auto">
      <svg
        width={svgWidth}
        height={svgHeight}
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        role="img"
        aria-label="Task dependency graph"
        className="w-full"
      >
        {/* Edges */}
        {graph.edges.map((edge, idx) => {
          const from = nodePositions.find((n) => n.id === edge.from);
          const to = nodePositions.find((n) => n.id === edge.to);
          if (!from || !to) return null;
          return (
            <g key={`edge-${idx}`}>
              <line
                x1={from.cx}
                y1={from.cy + nodeRadius}
                x2={to.cx}
                y2={to.cy - nodeRadius}
                stroke="var(--border)"
                strokeWidth="2"
                markerEnd="url(#arrowhead)"
              />
            </g>
          );
        })}

        {/* Arrow marker */}
        <defs>
          <marker
            id="arrowhead"
            markerWidth="8"
            markerHeight="6"
            refX="8"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 8 3, 0 6" fill="var(--border)" />
          </marker>
        </defs>

        {/* Nodes */}
        {nodePositions.map((node) => {
          const color = STATUS_NODE_COLORS[node.status] || STATUS_NODE_COLORS.pending;
          const isRunning = node.status === "running";
          return (
            <g key={node.id}>
              {/* Pulse ring for running */}
              {isRunning && (
                <circle
                  cx={node.cx}
                  cy={node.cy}
                  r={nodeRadius + 4}
                  fill="none"
                  stroke={color}
                  strokeWidth="2"
                  opacity="0.4"
                  className="animate-pulse-dot"
                />
              )}
              <circle
                cx={node.cx}
                cy={node.cy}
                r={nodeRadius}
                fill={color}
                opacity="0.9"
              />
              <text
                x={node.cx}
                y={node.cy + 4}
                textAnchor="middle"
                fill="white"
                fontSize="10"
                fontWeight="bold"
              >
                {node.label.slice(0, 3).toUpperCase()}
              </text>
              <text
                x={node.cx}
                y={node.cy + nodeRadius + 14}
                textAnchor="middle"
                fill="var(--muted-foreground)"
                fontSize="9"
              >
                {node.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
