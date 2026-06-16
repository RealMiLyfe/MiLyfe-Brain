"use client";

import { Moon, Sun } from "lucide-react";
import { useBrainStore } from "@/lib/store";

export function ThemeToggle() {
  const { isDark, toggleTheme } = useBrainStore();

  return (
    <button onClick={toggleTheme} className="p-2 rounded-lg hover:bg-gray-800 transition-colors" title="Toggle theme">
      {isDark ? <Sun className="w-5 h-5 text-yellow-400" /> : <Moon className="w-5 h-5 text-gray-400" />}
    </button>
  );
}
