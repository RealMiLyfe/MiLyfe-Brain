"use client";

import { Agent } from "@/lib/store";

const STATE_COLORS: Record<Agent["state"], string> = {
  idle: "bg-gray-500",
  working: "bg-[var(--primary)]",
  completed: "bg-[var(--success)]",
  failed: "bg-[var(--destructive)]",
};

const DOT_COLORS: Record<Agent["state"], string> = {
  idle: "bg-gray-400",
  working: "bg-[var(--primary)]",
  completed: "bg-[var(--success)]",
  failed: "bg-[var(--destructive)]",
};

interface AgentAvatarProps {
  agent: Agent;
  size?: "sm" | "md" | "lg";
}

export default function AgentAvatar({ agent, size = "md" }: AgentAvatarProps) {
  const sizeClasses = {
    sm: "w-8 h-8 text-xs",
    md: "w-10 h-10 text-sm",
    lg: "w-14 h-14 text-lg",
  };

  const dotSizes = {
    sm: "w-2 h-2",
    md: "w-2.5 h-2.5",
    lg: "w-3 h-3",
  };

  const letter = agent.role.charAt(0).toUpperCase();

  return (
    <div className="relative inline-flex" title={`${agent.role} (${agent.state})`}>
      <div
        className={`flex items-center justify-center rounded-full font-bold text-white ${sizeClasses[size]} ${STATE_COLORS[agent.state]} bg-opacity-80`}
        aria-label={`Agent ${agent.role}, status: ${agent.state}`}
      >
        {letter}
      </div>

      {/* Status dot */}
      <span
        className={`absolute bottom-0 right-0 rounded-full border-2 border-[var(--card)] ${dotSizes[size]} ${DOT_COLORS[agent.state]} ${
          agent.state === "working" ? "animate-pulse-dot" : ""
        }`}
      />
    </div>
  );
}
