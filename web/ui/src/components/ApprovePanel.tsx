import { useState } from "react";
import { api, GateCheck } from "../api";

interface Props {
  specId: string;
  onApproved: () => void;
}

export default function ApprovePanel({ specId, onApproved }: Props) {
  const [running, setRunning]   = useState(false);
  const [checks, setChecks]     = useState<GateCheck[] | null>(null);
  const [approved, setApproved] = useState(false);
  const [error, setError]       = useState("");

  async function handleCheck() {
    setRunning(true);
    setError("");
    setChecks(null);
    setApproved(false);
    try {
      const result = await api.approveSpec(specId);
      setChecks(result.checks);
      setApproved(result.approved);
      if (result.approved) onApproved();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Gate-Prüfung fehlgeschlagen.");
    } finally {
      setRunning(false);
    }
  }

  const allPassed = checks?.every(c => c.passed) ?? false;

  return (
    <section className="card" style={{ borderColor: approved ? "var(--green)" : "var(--accent)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ fontSize: 12, color: approved ? "var(--green)" : "var(--accent)", textTransform: "uppercase", letterSpacing: 1 }}>
          {approved ? "✓ Freigegeben" : "🔍 Zur Implementierung freigeben"}
        </h3>
        {!approved && (
          <button
            className="primary"
            onClick={handleCheck}
            disabled={running}
            style={{ fontSize: 12, padding: "5px 14px" }}
          >
            {running ? "⏳ Prüfe…" : "Gate-Prüfung starten"}
          </button>
        )}
      </div>

      {!checks && !running && !error && (
        <p style={{ fontSize: 13, color: "var(--muted)" }}>
          Prüft Validation, Contracts, Tests und KI-Analyse — setzt den Status auf <code>approved</code> wenn alle Gates bestanden sind.
        </p>
      )}

      {error && <p style={{ color: "var(--red)", fontSize: 13 }}>{error}</p>}

      {checks && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {checks.map(c => (
            <div key={c.name} style={{
              display: "flex", gap: 10, alignItems: "flex-start",
              padding: "8px 12px", borderRadius: 6,
              background: c.passed
                ? "color-mix(in srgb, var(--green) 10%, transparent)"
                : "color-mix(in srgb, var(--red) 10%, transparent)",
              border: `1px solid ${c.passed ? "var(--green)" : "var(--red)"}`,
            }}>
              <span style={{ fontSize: 16, flexShrink: 0 }}>{c.passed ? "✅" : "❌"}</span>
              <div>
                <strong style={{ fontSize: 13 }}>{c.name}</strong>
                <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>{c.message}</p>
              </div>
            </div>
          ))}

          {allPassed && (
            <p style={{ color: "var(--green)", fontSize: 13, marginTop: 4 }}>
              ✓ Alle Gates bestanden — Spec ist jetzt <code>approved</code>. Der Execute-Button erscheint oben.
            </p>
          )}
          {!allPassed && (
            <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 4 }}>
              Behebe die fehlgeschlagenen Punkte und starte die Prüfung erneut.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
