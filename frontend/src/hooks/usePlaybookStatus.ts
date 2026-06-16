"use client";

import { useEffect, useState } from "react";
import { playbookApi } from "@/lib/api";

export function usePlaybookStatus(playbookId: string | null, pollInterval = 2000) {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!playbookId) return;

    let active = true;
    setLoading(true);

    const poll = async () => {
      try {
        const data = await playbookApi.getStatus(playbookId);
        if (active) {
          setStatus(data);
          setLoading(false);

          // Stop polling if completed or failed
          if (data.status === "completed" || data.status === "failed") return;
        }
      } catch (err) {
        if (active) setLoading(false);
      }

      if (active) {
        setTimeout(poll, pollInterval);
      }
    };

    poll();

    return () => { active = false; };
  }, [playbookId, pollInterval]);

  return { status, loading };
}
