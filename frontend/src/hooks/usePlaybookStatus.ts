"use client";

import { useEffect, useState } from "react";
import { playbookApi } from "@/lib/api";

export function usePlaybookStatus(playbookId: string | null, intervalMs = 3000) {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!playbookId) return;

    const fetchStatus = async () => {
      setLoading(true);
      try {
        const s = await playbookApi.getStatus(playbookId);
        setStatus(s);
      } catch {}
      setLoading(false);
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, intervalMs);
    return () => clearInterval(interval);
  }, [playbookId, intervalMs]);

  return { status, loading };
}
