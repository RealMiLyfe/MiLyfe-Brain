"use client";

import { useEffect } from "react";
import { useBrainStore } from "@/lib/store";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const isDark = useBrainStore((s) => s.isDark);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
  }, [isDark]);

  return <>{children}</>;
}
