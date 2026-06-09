import { useEffect, useState } from "react";
import { api, Status, ValidationResult } from "../api";

interface Props { onShowAiUsage: () => void; onShowSettings: () => void; onShowServerInfo: () => void; onToggleConsole: () => void; onShowHub?: () => void; hubActive?: boolean; onShowDagMonitor?: () => void; dagMonitorActive?: boolean; }

export default function StatusBar({ onShowAiUsage, onShowSettings, onShowServerInfo, onToggleConsole, onShowHub, hubActive, onShowDagMonitor, dagMonitorActive }: Props) {
  const [status, setStatus] = useState<Status | null>(null);
  const [validating, setValidating] = useState(false);
  const [result, setResult] = useState<ValidationResult | null>(null);

  useEffect(() => {
    api.getStatus().then(setStatus).catch(console.error);
  }, []);

  async function handleValidate() {
    setValidating(true);
    setResult(null);
    try {
      const r = await api.validate();
      setResult(r);
      const s = await api.getStatus();
      setStatus(s);
    } finally {
      setValidating(false);
    }
  }

  async function handleTrace() {
    await api.trace();
    alert("Traceability-Matrix aktualisiert.");
  }

  return (
    <div style={{ borderBottom: "1px solid var(--border)", background: "var(--surface)", padding: "10px 20px", display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap" }}>
      <span style={{ fontWeight: 700, color: "var(--accent)", fontSize: 16 }}>SDD Framer</span>

      {status && (
        <>
          <Stat label="Specs" value={status.specs} />
          <Stat label="Contracts" value={status.contracts} />
          <Stat label="Tests" value={status.tests} />
          <span className={status.gaps > 0 ? "gap" : "ok"}>
            {status.gaps > 0 ? `⚠ ${status.gaps} Lücken` : "✓ vollständig"}
          </span>
        </>
      )}

      <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
        <button onClick={handleValidate} disabled={validating}>
          {validating ? "…" : "▶ Validate"}
        </button>
        <button onClick={handleTrace}>↻ Trace</button>
        {onShowDagMonitor && (
          <button
            onClick={onShowDagMonitor}
            style={{
              color: dagMonitorActive ? "var(--accent)" : "var(--muted)",
              borderColor: dagMonitorActive ? "var(--accent)" : "var(--border)",
            }}
          >
            ◈ DAG
          </button>
        )}
        {onShowHub && (
          <button
            onClick={onShowHub}
            style={{
              color: hubActive ? "var(--green)" : "var(--muted)",
              borderColor: hubActive ? "var(--green)" : "var(--border)",
            }}
          >
            ⬡ Hub
          </button>
        )}
        <button onClick={onShowAiUsage} style={{ color: "var(--accent)", borderColor: "var(--accent)" }}>
          ✦ KI-Kosten
        </button>
        <button onClick={onShowServerInfo} style={{ color: "var(--muted)", borderColor: "var(--border)" }}>
          ⬛ QR
        </button>
        <button onClick={onShowSettings} style={{ color: "var(--muted)", borderColor: "var(--border)" }}>
          ⚙ Einstellungen
        </button>
        <button onClick={onToggleConsole} style={{ color: "var(--muted)", borderColor: "var(--border)", fontFamily: "monospace" }}>
          &gt;_ Konsole
        </button>
      </div>

      {result && (
        <div style={{ width: "100%", marginTop: 6 }}>
          {result.ok && !result.warnings.length
            ? <span className="ok">✓ Alles in Ordnung</span>
            : (
              <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                {result.errors.map((e, i) => (
                  <span key={i} className="gap">✗ {e.file}: {e.message}</span>
                ))}
                {result.warnings.map((w, i) => (
                  <span key={i} style={{ color: "var(--yellow)" }}>⚠ {w.file}: {w.message}</span>
                ))}
              </div>
            )}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <span style={{ color: "var(--muted)", fontSize: 13 }}>
      {label}: <strong style={{ color: "var(--text)" }}>{value}</strong>
    </span>
  );
}
