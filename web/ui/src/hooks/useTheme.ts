import { useEffect, useState } from "react";

export type Theme = "dark" | "light" | "cyberpunk";

export const THEMES: { id: Theme; label: string; preview: string }[] = [
  { id: "dark",      label: "Gruvbox Dark", preview: "#282828" },
  { id: "light",     label: "Light",     preview: "#f4f4f8" },
  { id: "cyberpunk", label: "Cyberpunk", preview: "#0a0a0f" },
];

const STORAGE_KEY = "sdd-theme";
const DEFAULT: Theme = "dark";

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return (stored === "dark" || stored === "light" || stored === "cyberpunk")
      ? stored
      : DEFAULT;
  });

  useEffect(() => {
    applyTheme(theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  function setTheme(next: Theme) {
    setThemeState(next);
  }

  return { theme, setTheme };
}
