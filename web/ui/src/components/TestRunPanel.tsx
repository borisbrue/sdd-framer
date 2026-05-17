import { useCallback, useEffect, useState } from "react";
import { api, RunReport } from "../api";

interface Props {
  specId: string;
}

const STATUS_ICON: Record<string, string> = {
  passed:  "✓",
  failed:  "✗",
  error:   "✗",
  missing: "–",
  skipped: "◌",
};

const STATUS_COLOR: Record<string, string> = {
  passed:  "var(--green)",
  failed:  "var(--red)",
  error:   "var(--red)",
  missing: "var(--yellow)",
  skipped: "var(--muted)",
};

export default function TestRunPanel({ specId }: Props) {
  const [report, setReport]   = useState<RunReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  const fetchResults = useCallback(() => {
    setLoading(true);
    api.getTestResults(specId)
      .then(r => { setReport(r); setError(null); })
      .catch(() => { setReport(null); setError(null); })
      .finally(() => setLoading(false));
  }, [specId]);

  useEffect(() => { fetchResults(); }, [fetchResults]);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    try {
      const r = await api.triggerTestRun(specId);
      setReport(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unbekannter Fehler");
    } finally {
      setRunning(false);
    }
  };

  const sectionHead: React.CSSProperties = {
    fontSize: 12, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1,
  };

  return (
    <section className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={sectionHead}>Test Results</h3>
        <button onClick={handleRun} disabled={running} style={{ fontSize: 12 }}>
          {running ? "⏳ Läuft…" : "▶ Run Tests"}
        </button>
      </div>

      {error && (
        <p style={{ color: "var(--red)", fontSize: 13, marginBottom: 10 }}>✗ {error}</p>
      )}

      {loading && !running && (
        <p style={{ color: "var(--muted)", fontSize: 13 }}>Lade…</p>
      )}

      {!loading && !report && !error && (
        <p style={{ color: "var(--muted)", fontSize: 13 }}>
          Noch kein Test-Run. Klicke <strong>▶ Run Tests</strong> um zu starten.
        </p>
      )}

      {report && (
        <>
          {/* Zusammenfassung */}
          <div style={{ display: "flex", gap: 16, fontSize: 13, marginBottom: 12, flexWrap: "wrap" }}>
            <span style={{ color: "var(--green)" }}>✓ {report.passed} passed</span>
            <span style={{ color: report.failed > 0 ? "var(--red)" : "var(--muted)" }}>
              ✗ {report.failed} failed
            </span>
            <span style={{ color: "var(--muted)" }}>◌ {report.skipped} skipped</span>
            <span style={{ color: "var(--muted)", marginLeft: "auto" }}>
              {report.duration_s.toFixed(2)}s · {report.started_at.slice(0, 19).replace("T", " ")}
            </span>
          </div>

          {/* Tabelle */}
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ color: "var(--muted)", textAlign: "left" }}>
                <th style={th}>TST-ID</th>
                <th style={th}>Status</th>
                <th style={th}>Artefakt</th>
                <th style={{ ...th, textAlign: "right" }}>Dauer</th>
              </tr>
            </thead>
            <tbody>
              {report.tests.map(t => (
                <tr key={t.test_id} style={{ borderTop: "1px solid var(--border)" }}>
                  <td style={{ ...td, fontFamily: "monospace", color: "var(--accent)" }}>{t.test_id}</td>
                  <td style={{ ...td, color: STATUS_COLOR[t.status] ?? "var(--text)" }}>
                    {STATUS_ICON[t.status]} {t.status}
                  </td>
                  <td style={{ ...td, color: "var(--muted)", maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {t.artifact || "—"}
                  </td>
                  <td style={{ ...td, textAlign: "right", color: "var(--muted)" }}>
                    {t.duration_s > 0 ? `${t.duration_s.toFixed(2)}s` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Fehlermeldungen */}
          {report.tests.filter(t => t.message).map(t => (
            <details key={t.test_id} style={{ marginTop: 8 }}>
              <summary style={{ fontSize: 12, color: STATUS_COLOR[t.status], cursor: "pointer" }}>
                {t.test_id} – Fehlermeldung
              </summary>
              <pre style={{
                marginTop: 6, padding: "8px 12px", background: "var(--surface)",
                borderRadius: 4, fontSize: 11, overflowX: "auto",
                color: "var(--red)", whiteSpace: "pre-wrap",
              }}>
                {t.message}
              </pre>
            </details>
          ))}

          {/* Contract-Coverage */}
          {Object.keys(report.contract_coverage).length > 0 && (
            <div style={{ marginTop: 14, paddingTop: 10, borderTop: "1px solid var(--border)" }}>
              <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>
                Contract-Coverage
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {Object.entries(report.contract_coverage).map(([con, covered]) => (
                  <span key={con} style={{
                    fontSize: 11, padding: "2px 8px", borderRadius: 4,
                    background: "var(--surface)",
                    color: covered ? "var(--green)" : "var(--red)",
                    border: `1px solid ${covered ? "var(--green)" : "var(--red)"}`,
                  }}>
                    {covered ? "✓" : "✗"} {con}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}

const th: React.CSSProperties = {
  padding: "4px 8px", fontWeight: 600, fontSize: 11,
};

const td: React.CSSProperties = {
  padding: "5px 8px",
};
