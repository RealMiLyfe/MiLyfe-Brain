"use client";

import { useState, useEffect, useRef } from "react";
import { playbookApi, PlaybookStatusResponse } from "@/lib/api";

export function usePlaybookStatus(playbookId: string | null) {
  const [status, setStatus] = useState<PlaybookStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!playbookId) {
      setStatus(null);
      return;
    }

    let cancelled = false;

    async function poll() {
      if (cancelled) return;
      setLoading(true);
      try {
        const data = await playbookApi.getStatus(playbookId!);
        if (!cancelled) {
          setStatus(data);
          // Stop polling if terminal state
          if (
            data.status === "completed" ||
            data.status === "failed" ||
            data.status === "cancelled"
          ) {
            if (intervalRef.current) {
              clearInterval(intervalRef.current);
              intervalRef.current = null;
            }
          }
        }
      } catch {
        // Silently handle errors during polling
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    poll();
    intervalRef.current = setInterval(poll, 3000);

    return () => {
      cancelled = true;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [playbookId]);

  return { status, loading };
}
