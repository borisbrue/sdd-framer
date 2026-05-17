import { useState } from "react";
import { api } from "../api";

interface Props {
  absFile: string;
  line?: number;
  label?: string;
}

export default function OpenButton({ absFile, line, label = "In VS Code öffnen" }: Props) {
  const [state, setState] = useState<"idle" | "ok" | "err">("idle");

  async function handle() {
    try {
      await api.openInEditor(absFile, line);
      setState("ok");
      setTimeout(() => setState("idle"), 2000);
    } catch {
      setState("err");
      setTimeout(() => setState("idle"), 3000);
    }
  }

  return (
    <button
      onClick={handle}
      title={absFile}
      style={{ fontSize: 12, padding: "4px 10px", display: "flex", alignItems: "center", gap: 5 }}
    >
      <span>⌨</span>
      <span>{state === "ok" ? "Geöffnet ✓" : state === "err" ? "Fehler ✗" : label}</span>
    </button>
  );
}
