"use client";

import { AgentState } from "@/lib/store";

const ROLE_ICONS: Record<string, string> = {
  orchestrator: "O",
  researcher: "R",
  coder: "C",
  executor: "X",
  critic: "J",
  designer: "A",
  writer: "W",
  debugger: "D",
  planner: "P",
};

interface AgentAvatarProps {
  agent: AgentState;
  size?: "sm" | "md" | "lg";
  showStatus?: boolean;
  showName?: boolean;
}

export default function AgentAvatar({ agent, size = "md", showStatus = true, showName = false }: AgentAvatarProps) {
  const sizes = { sm: "w-8 h-8 text-xs", md: "w-10 h-10 text-sm", lg: "w-14 h-14 text-lg" };
  const dotSizes = { sm: "w-2 h-2", md: "w-2.5 h-2.5", lg: "w-3 h-3" };

  const statusColors: Record<string, string> = {
    idle: "bg-gray-400",
    working: "bg-blue-400 animate-pulse",
    completed: "bg-green-400",
    failed: "bg-red-400",
  };

  const statusAnimations: Record<string, string> = {
    idle: "",
    working: "animate-spin-slow",
    completed: "",
    failed: "animate-bounce-subtle",
  };

  return (
    <div className="flex items-center gap-2" title={`${agent.name} (${agent.role}) - ${agent.status}`}>
      <div className="relative">
        {/* Avatar circle */}
        <div
          className={`${sizes[size]} rounded-full flex items-center justify-center font-bold border-2 ${statusAnimations[agent.status] || ""}`}
          style={{
            backgroundColor: `${agent.avatar_color}20`,
            borderColor: agent.avatar_color,
            color: agent.avatar_color,
          }}
          role="img"
          aria-label={`${agent.name} agent`}
        >
          {ROLE_ICONS[agent.role] || "?"}
        </div>

        {/* Status dot */}
        {showStatus && (
          <div
            className={`absolute -bottom-0.5 -right-0.5 ${dotSizes[size]} rounded-full border border-[var(--card)] ${statusColors[agent.status] || statusColors.idle}`}
            aria-label={`Status: ${agent.status}`}
          />
        )}
      </div>

      {/* Name + task */}
      {showName && (
        <div className="min-w-0">
          <p className="text-xs font-medium truncate">{agent.name}</p>
          {agent.current_task && (
            <p className="text-[10px] text-[var(--muted-foreground)] truncate max-w-[120px]">{agent.current_task}</p>
          )}
        </div>
      )}
    </div>
  );
}

/** Row of active agent avatars */
export function AgentAvatarRow({ agents }: { agents: AgentState[] }) {
  if (agents.length === 0) return null;
  return (
    <div className="flex items-center gap-1" role="group" aria-label="Active agents">
      {agents.map((agent) => (
        <AgentAvatar key={agent.id} agent={agent} size="sm" showStatus showName={false} />
      ))}
    </div>
  );
}
