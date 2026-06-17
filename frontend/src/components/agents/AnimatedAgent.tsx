"use client";

import { motion, AnimatePresence } from "framer-motion";
import { clsx } from "clsx";

interface AnimatedAgentProps {
  role: string;
  name?: string;
  status?: "idle" | "active" | "busy" | "retired";
  size?: "sm" | "md" | "lg" | "xl";
  showLabel?: boolean;
  showThought?: string;
}

// SVG-based animated agent characters with personality
const AGENT_CHARS: Record<string, { emoji: string; color: string; bgFrom: string; bgTo: string; personality: string }> = {
  orchestrator: { emoji: "O", color: "#8b5cf6", bgFrom: "from-violet-400", bgTo: "to-purple-600", personality: "The Conductor" },
  researcher: { emoji: "R", color: "#ec4899", bgFrom: "from-pink-400", bgTo: "to-rose-600", personality: "The Explorer" },
  coder: { emoji: "C", color: "#06b6d4", bgFrom: "from-cyan-400", bgTo: "to-blue-600", personality: "The Builder" },
  executor: { emoji: "E", color: "#10b981", bgFrom: "from-emerald-400", bgTo: "to-green-600", personality: "The Runner" },
  critic: { emoji: "Cr", color: "#f59e0b", bgFrom: "from-amber-400", bgTo: "to-orange-600", personality: "The Judge" },
  designer: { emoji: "D", color: "#6366f1", bgFrom: "from-indigo-400", bgTo: "to-violet-600", personality: "The Architect" },
  writer: { emoji: "W", color: "#f97316", bgFrom: "from-orange-400", bgTo: "to-red-500", personality: "The Scribe" },
  debugger: { emoji: "Db", color: "#ef4444", bgFrom: "from-red-400", bgTo: "to-rose-600", personality: "The Detective" },
  planner: { emoji: "P", color: "#8b5cf6", bgFrom: "from-purple-400", bgTo: "to-indigo-600", personality: "The Strategist" },
};

const SIZE_CONFIG = {
  sm: { container: "w-10 h-10", text: "text-xs", font: "text-[10px]", thought: "text-[9px]" },
  md: { container: "w-14 h-14", text: "text-sm", font: "text-xs", thought: "text-[10px]" },
  lg: { container: "w-20 h-20", text: "text-lg", font: "text-sm", thought: "text-xs" },
  xl: { container: "w-28 h-28", text: "text-2xl", font: "text-base", thought: "text-sm" },
};

// Animation variants based on status
const idleAnimation = {
  y: [0, -3, 0],
  transition: { duration: 3, repeat: Infinity, ease: "easeInOut" },
};

const activeAnimation = {
  scale: [1, 1.05, 1],
  rotate: [0, 2, -2, 0],
  transition: { duration: 1.5, repeat: Infinity, ease: "easeInOut" },
};

const busyAnimation = {
  scale: [1, 1.08, 1],
  transition: { duration: 0.8, repeat: Infinity, ease: "easeInOut" },
};

const retiredAnimation = {
  opacity: 0.4,
  scale: 0.9,
};

export function AnimatedAgent({
  role,
  name,
  status = "idle",
  size = "md",
  showLabel = false,
  showThought,
}: AnimatedAgentProps) {
  const char = AGENT_CHARS[role.toLowerCase()] || AGENT_CHARS.orchestrator;
  const sizeConfig = SIZE_CONFIG[size];

  const getAnimation = () => {
    switch (status) {
      case "active": return activeAnimation;
      case "busy": return busyAnimation;
      case "retired": return retiredAnimation;
      default: return idleAnimation;
    }
  };

  return (
    <div className="flex flex-col items-center gap-1.5 relative">
      {/* Thought bubble */}
      <AnimatePresence>
        {showThought && status === "active" && (
          <motion.div
            initial={{ opacity: 0, y: 5, scale: 0.8 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 5, scale: 0.8 }}
            className="absolute -top-8 left-1/2 -translate-x-1/2 z-10"
          >
            <div className="relative bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1 shadow-md max-w-[120px]">
              <p className={clsx("text-slate-600 dark:text-slate-300 truncate", sizeConfig.thought)}>
                {showThought}
              </p>
              {/* Triangle pointer */}
              <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-white dark:bg-slate-700 border-r border-b border-slate-200 dark:border-slate-600 rotate-45" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Agent body */}
      <div className="relative">
        {/* Glow ring for active state */}
        {(status === "active" || status === "busy") && (
          <motion.div
            animate={{ scale: [1, 1.4, 1], opacity: [0.4, 0, 0.4] }}
            transition={{ duration: 2, repeat: Infinity }}
            className={clsx(
              "absolute inset-0 rounded-full bg-gradient-to-r",
              char.bgFrom, char.bgTo,
              "blur-sm"
            )}
          />
        )}

        {/* Main avatar */}
        <motion.div
          animate={getAnimation()}
          className={clsx(
            "relative rounded-full flex items-center justify-center",
            "bg-gradient-to-br shadow-lg border-2 border-white dark:border-slate-700",
            char.bgFrom, char.bgTo,
            sizeConfig.container
          )}
        >
          {/* Inner face */}
          <div className="flex flex-col items-center justify-center">
            <span className={clsx("font-bold text-white drop-shadow-sm", sizeConfig.text)}>
              {char.emoji}
            </span>
            {/* Eyes that blink */}
            {size !== "sm" && (
              <motion.div
                className="flex gap-1 mt-0.5"
                animate={{ scaleY: [1, 0.1, 1] }}
                transition={{ duration: 0.15, repeat: Infinity, repeatDelay: 4 }}
              >
                <div className="w-1 h-1 rounded-full bg-white/80" />
                <div className="w-1 h-1 rounded-full bg-white/80" />
              </motion.div>
            )}
          </div>
        </motion.div>

        {/* Status badge */}
        <div
          className={clsx(
            "absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-2 border-white dark:border-slate-800",
            status === "active" && "bg-green-500",
            status === "busy" && "bg-amber-500",
            status === "idle" && "bg-slate-400",
            status === "retired" && "bg-red-400"
          )}
        />

        {/* Working particles (only when busy) */}
        {status === "busy" && (
          <>
            <motion.div
              animate={{ y: [-2, -12], x: [0, 5], opacity: [1, 0] }}
              transition={{ duration: 1.2, repeat: Infinity, delay: 0 }}
              className="absolute top-0 left-1/2 w-1 h-1 rounded-full bg-yellow-400"
            />
            <motion.div
              animate={{ y: [-2, -10], x: [0, -4], opacity: [1, 0] }}
              transition={{ duration: 1, repeat: Infinity, delay: 0.4 }}
              className="absolute top-0 left-1/3 w-1 h-1 rounded-full bg-cyan-400"
            />
            <motion.div
              animate={{ y: [-2, -14], x: [0, 2], opacity: [1, 0] }}
              transition={{ duration: 1.4, repeat: Infinity, delay: 0.8 }}
              className="absolute top-0 right-1/3 w-1 h-1 rounded-full bg-pink-400"
            />
          </>
        )}
      </div>

      {/* Label */}
      {showLabel && (
        <div className="text-center">
          <p className={clsx("font-semibold capitalize", sizeConfig.font)} style={{ color: char.color }}>
            {char.personality}
          </p>
          {name && (
            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate max-w-[90px]">
              {name}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
