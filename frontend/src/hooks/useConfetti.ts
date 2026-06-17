"use client";

import { useCallback } from "react";

/**
 * Hook that triggers a confetti celebration.
 * Uses canvas-confetti for the particle effect.
 */
export function useConfetti() {
  const fire = useCallback(async () => {
    try {
      const confetti = (await import("canvas-confetti")).default;
      // Multi-burst celebration
      const end = Date.now() + 800;
      const colors = ["#6366f1", "#10b981", "#f59e0b", "#ec4899", "#06b6d4"];

      const frame = () => {
        confetti({
          particleCount: 3,
          angle: 60,
          spread: 55,
          origin: { x: 0, y: 0.7 },
          colors,
        });
        confetti({
          particleCount: 3,
          angle: 120,
          spread: 55,
          origin: { x: 1, y: 0.7 },
          colors,
        });
        if (Date.now() < end) requestAnimationFrame(frame);
      };
      frame();

      // Big burst in center
      confetti({
        particleCount: 80,
        spread: 100,
        origin: { y: 0.6 },
        colors,
      });
    } catch {
      // canvas-confetti not loaded, skip silently
    }
  }, []);

  return { fire };
}
