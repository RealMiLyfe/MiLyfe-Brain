"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { getPlaybookStatus, type PlaybookStatus, type PlaybookStep } from "@/lib/api";

interface PlaybookStatusData {
  status: PlaybookStatus;
  progress: number;
  currentStep?: string;
  steps: PlaybookStep[];
  error: string | null;
  isLoading: boolean;
}

export function usePlaybookStatus(
  playbookId: string | null,
  pollInterval: number = 2000
): PlaybookStatusData {
  const [status, setStatus] = useState<PlaybookStatus>("draft");
  const [progress, setProgress] = useState<number>(0);
  const [currentStep, setCurrentStep] = useState<string | undefined>();
  const [steps, setSteps] = useState<PlaybookStep[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!playbookId) return;

    try {
      setIsLoading(true);
      const data = await getPlaybookStatus(playbookId);
      setStatus(data.status);
      setProgress(data.progress);
      setCurrentStep(data.current_step);
      setSteps(data.steps);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch status");
    } finally {
      setIsLoading(false);
    }
  }, [playbookId]);

  useEffect(() => {
    if (!playbookId) {
      setStatus("draft");
      setProgress(0);
      setSteps([]);
      return;
    }

    // Initial fetch
    fetchStatus();

    // Start polling only if playbook is active
    const isActive = status === "running" || status === "draft";
    if (isActive) {
      intervalRef.current = setInterval(fetchStatus, pollInterval);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [playbookId, pollInterval, fetchStatus, status]);

  // Stop polling when playbook completes
  useEffect(() => {
    if (
      status === "completed" ||
      status === "failed" ||
      status === "cancelled"
    ) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  }, [status]);

  return { status, progress, currentStep, steps, error, isLoading };
}
