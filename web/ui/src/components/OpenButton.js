import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { api } from "../api";
export default function OpenButton({ absFile, line, label = "In VS Code öffnen" }) {
    const [state, setState] = useState("idle");
    async function handle() {
        try {
            await api.openInEditor(absFile, line);
            setState("ok");
            setTimeout(() => setState("idle"), 2000);
        }
        catch {
            setState("err");
            setTimeout(() => setState("idle"), 3000);
        }
    }
    return (_jsxs("button", { onClick: handle, title: absFile, style: { fontSize: 12, padding: "4px 10px", display: "flex", alignItems: "center", gap: 5 }, children: [_jsx("span", { children: "\u2328" }), _jsx("span", { children: state === "ok" ? "Geöffnet ✓" : state === "err" ? "Fehler ✗" : label })] }));
}
