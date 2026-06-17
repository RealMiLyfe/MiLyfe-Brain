"use client";

import { useTheme } from "./ThemeProvider";

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const options: Array<{ value: "dark" | "light" | "system"; label: string }> = [
    { value: "dark", label: "D" },
    { value: "light", label: "L" },
    { value: "system", label: "S" },
  ];

  return (
    <div className="flex items-center gap-1 p-0.5 bg-[var(--muted)] rounded-lg" role="radiogroup" aria-label="Theme">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => setTheme(opt.value)}
          className={`px-2 py-1 text-xs rounded ${theme === opt.value ? "bg-[var(--card)] text-[var(--foreground)] shadow-sm" : "text-[var(--muted-foreground)]"}`}
          role="radio"
          aria-checked={theme === opt.value}
          aria-label={opt.value}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
