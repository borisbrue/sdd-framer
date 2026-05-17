import { useEffect, useState } from "react";
export const THEMES = [
    { id: "dark", label: "Gruvbox Dark", preview: "#282828" },
    { id: "light", label: "Light", preview: "#f4f4f8" },
    { id: "cyberpunk", label: "Cyberpunk", preview: "#0a0a0f" },
];
const STORAGE_KEY = "sdd-theme";
const DEFAULT = "dark";
function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
}
export function useTheme() {
    const [theme, setThemeState] = useState(() => {
        const stored = localStorage.getItem(STORAGE_KEY);
        return (stored === "dark" || stored === "light" || stored === "cyberpunk")
            ? stored
            : DEFAULT;
    });
    useEffect(() => {
        applyTheme(theme);
        localStorage.setItem(STORAGE_KEY, theme);
    }, [theme]);
    function setTheme(next) {
        setThemeState(next);
    }
    return { theme, setTheme };
}
