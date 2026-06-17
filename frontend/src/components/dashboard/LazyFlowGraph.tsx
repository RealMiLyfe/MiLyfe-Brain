"use client";

import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";
import type { PlaybookStep } from "@/lib/api";

// Lazy-load React Flow to reduce initial bundle size (~200KB)
const FlowGraph = dynamic(
  () => import("./FlowGraph").then((mod) => ({ default: mod.FlowGraph })),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-[400px] border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50 dark:bg-slate-900/50">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
          <span className="text-xs text-slate-400">Loading graph...</span>
        </div>
      </div>
    ),
  }
);

export function LazyFlowGraph({ steps }: { steps: PlaybookStep[] }) {
  return <FlowGraph steps={steps} />;
}
