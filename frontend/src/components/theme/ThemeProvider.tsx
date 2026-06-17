"use client";

import { createContext, useContext, useEffect, useState } from "react";

type Theme = "dark" | "light" | "system";
interface ThemeContextType { theme: Theme; setTheme: (t: Theme) => void; resolved: "dark" | "light"; }

const ThemeContext = createContext<ThemeContextType>({ theme: "dark", setTheme: () => {}, resolved: "dark" });

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");
  const [resolved, setResolved] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const stored = localStorage.getItem("milyfe-theme") as Theme | null;
    if (stored) setThemeState(stored);
  }, []);

  useEffect(() => {
    localStorage.setItem("milyfe-theme", theme);
    const r = theme === "system" ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light") : theme;
    setResolved(r);
    document.documentElement.classList.toggle("dark", r === "dark");
    document.documentElement.classList.toggle("light", r === "light");
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme: setThemeState, resolved }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() { return useContext(ThemeContext); }
