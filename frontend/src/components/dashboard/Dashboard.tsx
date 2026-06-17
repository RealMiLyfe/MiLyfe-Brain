"use client";

import { useEffect, useState } from "react";
import { useBrainStore } from "@/lib/store";
import { usePlaybookStatus } from "@/hooks/usePlaybookStatus";
import { PlaybookProgress } from "./PlaybookProgress";
import { EventLog } from "./EventLog";
import { WorkspaceFiles } from "./WorkspaceFiles";
import { DownloadButton } from "./DownloadButton";
import { AgentAvatar } from "@/components/agents/AgentAvatar";

export function Dashboard() {
  const currentPlaybook = useBrainStore((s) => s.currentPlaybook);
  const events = useBrainStore((s) => s.events);
  const { status } = usePlaybookStatus(currentPlaybook?.id || null);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{currentPlaybook?.title || "Dashboard"}</h1>
          <p className="text-sm text-gray-400">{currentPlaybook?.description?.slice(0, 100)}</p>
        </div>
        <DownloadButton />
      </div>

      {/* Progress */}
      <PlaybookProgress status={status} />

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Event Log */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h2 className="text-lg font-semibold text-white mb-3">Live Events</h2>
          <EventLog events={events} />
        </div>

        {/* Workspace Files */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h2 className="text-lg font-semibold text-white mb-3">Workspace Files</h2>
          <WorkspaceFiles />
        </div>
      </div>

      {/* Active Agents */}
      {status?.steps && status.steps.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h2 className="text-lg font-semibold text-white mb-3">Steps</h2>
          <div className="space-y-2">
            {status.steps.map((step: any, i: number) => (
              <div key={step.id || i} className="flex items-center gap-3 p-2 rounded bg-gray-800/50">
                <AgentAvatar role={step.agent_role} size="sm" />
                <div className="flex-1">
                  <p className="text-sm text-white">{step.description?.slice(0, 80)}</p>
                  <p className="text-xs text-gray-500">{step.agent_role}</p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  step.status === "completed" ? "bg-green-500/20 text-green-400" :
                  step.status === "running" ? "bg-blue-500/20 text-blue-400" :
                  step.status === "failed" ? "bg-red-500/20 text-red-400" :
                  "bg-gray-700 text-gray-400"
                }`}>
                  {step.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
