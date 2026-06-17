"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx } from "clsx";
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Rewind,
  FastForward,
  Clock,
  CheckCircle2,
  XCircle,
  Zap,
  Brain,
  Wrench,
} from "lucide-react";
import type { PlaybookStep } from "@/lib/api";

interface TimelineEvent {
  id: string;
  timestamp: number; // relative ms from start
  type: "step_started" | "thought" | "action" | "step_completed" | "step_failed" | "agent_spawned";
  agentRole?: string;
  description: string;
  details?: string;
}

interface StoryReplayProps {
  steps: PlaybookStep[];
  title: string;
  startedAt?: string;
  completedAt?: string;
}

// Generate timeline events from playbook steps
function generateTimeline(steps: PlaybookStep[], startedAt?: string): TimelineEvent[] {
  const events: TimelineEvent[] = [];
  const baseTime = startedAt ? new Date(startedAt).getTime() : 0;

  steps.forEach((step, idx) => {
    const stepStart = step.started_at ? new Date(step.started_at).getTime() - baseTime : idx * 5000;
    const stepEnd = step.completed_at ? new Date(step.completed_at).getTime() - baseTime : stepStart + 4000;

    // Agent spawned
    events.push({
      id: `${step.id}-spawn`,
      timestamp: stepStart,
      type: "agent_spawned",
      agentRole: step.agent_role,
      description: `${step.agent_role || "Agent"} spawned for task`,
    });

    // Step started
    events.push({
      id: `${step.id}-start`,
      timestamp: stepStart + 200,
      type: "step_started",
      agentRole: step.agent_role,
      description: step.name,
      details: `Step ${idx + 1} of ${steps.length}`,
    });

    // Simulated thought (midpoint)
    events.push({
      id: `${step.id}-thought`,
      timestamp: stepStart + (stepEnd - stepStart) * 0.4,
      type: "thought",
      agentRole: step.agent_role,
      description: `Analyzing: "${step.name.slice(0, 50)}"`,
    });

    // Action
    events.push({
      id: `${step.id}-action`,
      timestamp: stepStart + (stepEnd - stepStart) * 0.7,
      type: "action",
      agentRole: step.agent_role,
      description: "Executing tools...",
      details: step.output?.slice(0, 100),
    });

    // Completion
    events.push({
      id: `${step.id}-end`,
      timestamp: stepEnd,
      type: step.status === "failed" ? "step_failed" : "step_completed",
      agentRole: step.agent_role,
      description: step.status === "failed" ? `Failed: ${step.name}` : `Completed: ${step.name}`,
      details: step.output?.slice(0, 150),
    });
  });

  return events.sort((a, b) => a.timestamp - b.timestamp);
}

const EVENT_ICONS: Record<string, { icon: typeof Zap; color: string }> = {
  agent_spawned: { icon: Brain, color: "text-purple-500" },
  step_started: { icon: Play, color: "text-blue-500" },
  thought: { icon: Brain, color: "text-indigo-400" },
  action: { icon: Wrench, color: "text-amber-500" },
  step_completed: { icon: CheckCircle2, color: "text-green-500" },
  step_failed: { icon: XCircle, color: "text-red-500" },
};

export function StoryReplay({ steps, title, startedAt, completedAt }: StoryReplayProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [speed, setSpeed] = useState(1);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const timeline = generateTimeline(steps, startedAt);
  const totalDuration = timeline.length > 0 ? timeline[timeline.length - 1].timestamp + 1000 : 10000;

  // Visible events (up to current time)
  const visibleEvents = timeline.filter((e) => e.timestamp <= currentTime);
  const currentEventIdx = visibleEvents.length - 1;

  // Playback controls
  const play = useCallback(() => {
    setIsPlaying(true);
  }, []);

  const pause = useCallback(() => {
    setIsPlaying(false);
  }, []);

  const restart = useCallback(() => {
    setCurrentTime(0);
    setIsPlaying(true);
  }, []);

  const skipToEnd = useCallback(() => {
    setCurrentTime(totalDuration);
    setIsPlaying(false);
  }, [totalDuration]);

  const skipForward = useCallback(() => {
    const nextEvent = timeline.find((e) => e.timestamp > currentTime);
    if (nextEvent) setCurrentTime(nextEvent.timestamp);
  }, [currentTime, timeline]);

  const skipBack = useCallback(() => {
    const prevEvents = timeline.filter((e) => e.timestamp < currentTime - 100);
    if (prevEvents.length > 0) setCurrentTime(prevEvents[prevEvents.length - 1].timestamp);
    else setCurrentTime(0);
  }, [currentTime, timeline]);

  // Animation loop
  useEffect(() => {
    if (isPlaying) {
      intervalRef.current = setInterval(() => {
        setCurrentTime((t) => {
          const next = t + 50 * speed;
          if (next >= totalDuration) {
            setIsPlaying(false);
            return totalDuration;
          }
          return next;
        });
      }, 50);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isPlaying, speed, totalDuration]);

  const progressPercent = totalDuration > 0 ? (currentTime / totalDuration) * 100 : 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
            Story Mode: {title}
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {timeline.length} events | {Math.round(totalDuration / 1000)}s duration
          </p>
        </div>
        <div className="flex items-center gap-1">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-xs font-mono text-slate-500">
            {Math.round(currentTime / 1000)}s / {Math.round(totalDuration / 1000)}s
          </span>
        </div>
      </div>

      {/* Progress bar / scrubber */}
      <div className="relative">
        <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden cursor-pointer"
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width;
            setCurrentTime(x * totalDuration);
          }}
        >
          <motion.div
            className="h-full bg-gradient-to-r from-primary-500 to-green-400 rounded-full"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        {/* Event markers on timeline */}
        <div className="absolute top-0 left-0 w-full h-2 pointer-events-none">
          {timeline.map((evt) => (
            <div
              key={evt.id}
              className={clsx(
                "absolute top-0 w-0.5 h-2",
                evt.type === "step_completed" ? "bg-green-400" :
                evt.type === "step_failed" ? "bg-red-400" :
                "bg-slate-400/50"
              )}
              style={{ left: `${(evt.timestamp / totalDuration) * 100}%` }}
            />
          ))}
        </div>
      </div>

      {/* Playback controls */}
      <div className="flex items-center justify-center gap-2">
        <button onClick={restart} className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500" title="Restart">
          <Rewind className="w-4 h-4" />
        </button>
        <button onClick={skipBack} className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500" title="Previous event">
          <SkipBack className="w-4 h-4" />
        </button>
        <button
          onClick={isPlaying ? pause : play}
          className="w-10 h-10 rounded-full bg-primary-600 hover:bg-primary-700 text-white flex items-center justify-center shadow-md"
        >
          {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
        </button>
        <button onClick={skipForward} className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500" title="Next event">
          <SkipForward className="w-4 h-4" />
        </button>
        <button onClick={skipToEnd} className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500" title="Skip to end">
          <FastForward className="w-4 h-4" />
        </button>

        {/* Speed control */}
        <div className="ml-4 flex items-center gap-1.5">
          {[0.5, 1, 2, 4].map((s) => (
            <button
              key={s}
              onClick={() => setSpeed(s)}
              className={clsx(
                "text-[10px] px-1.5 py-0.5 rounded font-medium transition-colors",
                speed === s
                  ? "bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300"
                  : "text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700"
              )}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>

      {/* Event timeline (scrollable, auto-follows) */}
      <div className="max-h-[300px] overflow-y-auto scrollbar-thin space-y-1 border border-slate-200 dark:border-slate-700 rounded-xl p-3 bg-slate-50 dark:bg-slate-900/50">
        <AnimatePresence>
          {visibleEvents.map((evt, idx) => {
            const config = EVENT_ICONS[evt.type] || EVENT_ICONS.action;
            const Icon = config.icon;
            const isLatest = idx === currentEventIdx;

            return (
              <motion.div
                key={evt.id}
                initial={{ opacity: 0, x: -10, height: 0 }}
                animate={{ opacity: isLatest ? 1 : 0.7, x: 0, height: "auto" }}
                className={clsx(
                  "flex items-start gap-2.5 py-1.5 px-2 rounded-lg transition-colors",
                  isLatest && "bg-white dark:bg-slate-800 shadow-sm border border-slate-200 dark:border-slate-700"
                )}
              >
                <Icon className={clsx("w-3.5 h-3.5 mt-0.5 flex-shrink-0", config.color)} />
                <div className="flex-1 min-w-0">
                  <p className={clsx("text-xs", isLatest ? "font-medium text-slate-800 dark:text-slate-100" : "text-slate-600 dark:text-slate-400")}>
                    {evt.description}
                  </p>
                  {evt.details && isLatest && (
                    <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">
                      {evt.details}
                    </p>
                  )}
                </div>
                {evt.agentRole && (
                  <span className="text-[9px] px-1 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400 font-mono flex-shrink-0">
                    {evt.agentRole}
                  </span>
                )}
              </motion.div>
            );
          })}
        </AnimatePresence>

        {visibleEvents.length === 0 && (
          <div className="text-center py-6 text-xs text-slate-400">
            Press play to start the story replay
          </div>
        )}
      </div>
    </div>
  );
}
