"use client";

import { motion } from "framer-motion";

const ROLE_COLORS: Record<string, string> = {
  orchestrator: "#6366f1",
  researcher: "#06b6d4",
  coder: "#10b981",
  executor: "#f59e0b",
  critic: "#ef4444",
  designer: "#8b5cf6",
  writer: "#ec4899",
  debugger: "#f97316",
  planner: "#14b8a6",
};

const ROLE_ICONS: Record<string, string> = {
  orchestrator: "C",
  researcher: "R",
  coder: "B",
  executor: "X",
  critic: "J",
  designer: "A",
  writer: "S",
  debugger: "D",
  planner: "P",
};

interface Props {
  role: string;
  size?: "sm" | "md" | "lg";
  active?: boolean;
}

export function AgentAvatar({ role, size = "md", active = false }: Props) {
  const color = ROLE_COLORS[role] || "#6b7280";
  const letter = ROLE_ICONS[role] || "?";
  const sizes = { sm: "w-6 h-6 text-xs", md: "w-8 h-8 text-sm", lg: "w-12 h-12 text-lg" };

  return (
    <motion.div
      className={`${sizes[size]} rounded-full flex items-center justify-center font-bold text-white relative`}
      style={{ backgroundColor: color }}
      animate={active ? { scale: [1, 1.1, 1] } : {}}
      transition={{ repeat: Infinity, duration: 2 }}
    >
      {letter}
      {active && (
        <motion.div
          className="absolute inset-0 rounded-full border-2"
          style={{ borderColor: color }}
          animate={{ scale: [1, 1.3], opacity: [0.8, 0] }}
          transition={{ repeat: Infinity, duration: 1.5 }}
        />
      )}
    </motion.div>
  );
}
