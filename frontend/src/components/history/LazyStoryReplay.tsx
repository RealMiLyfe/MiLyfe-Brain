"use client";

import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";
import type { PlaybookStep } from "@/lib/api";

// Lazy-load StoryReplay to keep history view fast
const StoryReplay = dynamic(
  () => import("./StoryReplay").then((mod) => ({ default: mod.StoryReplay })),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-32">
        <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
      </div>
    ),
  }
);

interface Props {
  steps: PlaybookStep[];
  title: string;
  startedAt?: string;
  completedAt?: string;
}

export function LazyStoryReplay(props: Props) {
  return <StoryReplay {...props} />;
}
