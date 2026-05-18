import { useCallback, useEffect, useState } from "react";
import { Project } from "../config";
import { getTestResults, triggerTestRun, TestReport, TestStatus } from "../api";

interface Props {
  project: Project;
  specId: string;
}

const STATUS_ICON: Record<TestStatus, string> = {
  passed:  "✓",
  failed:  "✗",
  error:   "✗",
  missing: "–",
  skipped: "◌",
};

const STATUS_COLOR: Record<TestStatus, string> = {
  passed:  "var(--green)",
  failed:  "var(--red)",
  error:   "var(--red)",
  missing: "var(--yellow)",
  skipped: "var(--muted)",
};

export default function TestRunPanel({ project, specId }: Props) {
  const [report, setReport]   = useState<TestReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError]     = useState("");

  const fetchResults = useCallback(() => {
    setLoading(true);
    getTestResults(project, specId)
      .then(r  => { setReport(r); setError(""); })
      .catch(() => { /* 404 = noch kein Run — kein Fehler */ })
      .finally(() => setLoading(false));
  }, [project, specId]);

  useEffect(() => { fetchResults(); }, [fetchResults]);

  async function handleRun() {
    setRunning(true);
    setError("");
    try {
      const r = await triggerTestRun(project, specId);
      setReport(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unbekannter Fehler");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div style={{
      background: "var(--surface)", borderRadius: 10,
      border: "1px solid var(--border)", overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "10px 14px", borderBottom: report ? "1px solid var(--border)" : "none",
      }}>
        <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1 }}>
          Test Results
        </span>
        <button
          onClick={handleRun}
          disabled={running}
          className="primary"
          style={{ fontSize: 12, padding: "4px 12px" }}
        >
          {running ? "⏳ Läuft…" : "▶ Run"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div style={{ padding: "8px 14px", color: "var(--red)", fontSize: 13 }}>
          ✗ {error}
        </div>
      )}

      {/* Loading */}
      {loading && !running && (
        <div style={{ padding: "12px 14px", color: "var(--muted)", fontSize: 13 }}>Laden…</div>
      )}

      {/* Kein Run */}
      {!loading && !report && !error && (
        <div style={{ padding: "12px 14px", color: "var(--muted)", fontSize: 13 }}>
          Noch kein Test-Run — tippe <strong>▶ Run</strong>.
        </div>
      )}

      {/* Ergebnisse */}
      {report && (
        <div style={{ padding: "10px 14px" }}>
          {/* Counters */}
          <div style={{ display: "flex", gap: 14, fontSize: 13, marginBottom: 10, flexWrap: "wrap" }}>
            <span style={{ color: "var(--green)" }}>✓ {report.passed} passed</span>
            <span style={{ color: report.failed > 0 ? "var(--red)" : "var(--muted)" }}>
              ✗ {report.failed} failed
            </span>
            <span style={{ color: "var(--muted)" }}>◌ {report.skipped} skipped</span>
            <span style={{ color: "var(--muted)", marginLeft: "auto", fontSize: 12 }}>
              {report.duration_s.toFixed(2)}s
            </span>
          </div>

          {/* Test-Tabelle */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {report.tests.map(t => (
              <div key={t.test_id}>
                <div style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "5px 0", borderTop: "1px solid var(--border)",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                    <span style={{ color: STATUS_COLOR[t.status] ?? "var(--text)", fontSize: 14, flexShrink: 0 }}>
                      {STATUS_ICON[t.status]}
                    </span>
                    <span style={{ fontFamily: "monospace", fontSize: 12, color: "var(--accent)", flexShrink: 0 }}>
                      {t.test_id}
                    </span>
                    {t.artifact && (
                      <span style={{
                        fontSize: 11, color: "var(--muted)",
                        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                      }}>
                        {t.artifact.split("/").pop()}
                      </span>
                    )}
                  </div>
                  <span style={{ fontSize: 11, color: "var(--muted)", flexShrink: 0, marginLeft: 8 }}>
                    {t.duration_s > 0 ? `${t.duration_s.toFixed(2)}s` : ""}
                  </span>
                </div>

                {/* Fehlermeldung aufklappbar */}
                {t.message && (
                  <details style={{ marginBottom: 4 }}>
                    <summary style={{ fontSize: 11, color: STATUS_COLOR[t.status], cursor: "pointer", paddingLeft: 22 }}>
                      Fehlermeldung
                    </summary>
                    <pre style={{
                      marginTop: 4, padding: "6px 10px",
                      background: "var(--bg)", borderRadius: 4,
                      fontSize: 11, color: "var(--red)",
                      whiteSpace: "pre-wrap", wordBreak: "break-word",
                      overflowX: "auto",
                    }}>
                      {t.message}
                    </pre>
                  </details>
                )}
              </div>
            ))}
          </div>

          {/* Contract Coverage */}
          {Object.keys(report.contract_coverage).length > 0 && (
            <div style={{ marginTop: 12, paddingTop: 10, borderTop: "1px solid var(--border)" }}>
              <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>
                Contract-Coverage
              </div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {Object.entries(report.contract_coverage).map(([con, covered]) => (
                  <span key={con} style={{
                    fontSize: 11, padding: "2px 8px", borderRadius: 4,
                    background: "var(--bg)",
                    color: covered ? "var(--green)" : "var(--red)",
                    border: `1px solid ${covered ? "var(--green)" : "var(--red)"}`,
                  }}>
                    {covered ? "✓" : "✗"} {con}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div style={{ marginTop: 8, fontSize: 11, color: "var(--muted)" }}>
            {report.started_at.slice(0, 19).replace("T", " ")} · {report.runner}
          </div>
        </div>
      )}
    </div>
  );
}
