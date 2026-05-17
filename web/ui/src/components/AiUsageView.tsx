import { AiUsage } from "../api";

interface Props {
  usage: AiUsage;
  onClose: () => void;
}

export default function AiUsageView({ usage, onClose }: Props) {
  const s = usage.summary;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ fontSize: 18, fontWeight: 700 }}>✦ KI-Nutzung</h2>
        <button onClick={onClose} style={{ fontSize: 12, padding: "3px 10px" }}>× Schließen</button>
      </div>

      {/* Summary */}
      <div className="card">
        <h3 style={head}>Zusammenfassung</h3>
        <div style={{ display: "flex", gap: 24, flexWrap: "wrap", marginTop: 10 }}>
          <Stat label="Aufrufe" value={String(s.total_calls)} />
          <Stat label="Gesamtkosten" value={`$${s.total_cost_usd.toFixed(4)}`} accent />
          <Stat label="Input-Tokens" value={s.total_input_tokens.toLocaleString()} />
          <Stat label="Output-Tokens" value={s.total_output_tokens.toLocaleString()} />
          <Stat label="Cache-Reads" value={s.total_cache_read_tokens.toLocaleString()} />
          <Stat label="Cache-Writes" value={s.total_cache_creation_tokens.toLocaleString()} />
        </div>
      </div>

      {/* By provider */}
      {Object.keys(s.by_provider ?? {}).length > 0 && (
        <div className="card">
          <h3 style={head}>Nach Provider</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, marginTop: 10 }}>
            <thead>
              <tr style={{ color: "var(--muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1 }}>
                <th style={th}>Provider</th>
                <th style={{ ...th, textAlign: "right" }}>Aufrufe</th>
                <th style={{ ...th, textAlign: "right" }}>Input-Tokens</th>
                <th style={{ ...th, textAlign: "right" }}>Output-Tokens</th>
                <th style={{ ...th, textAlign: "right" }}>Kosten</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(s.by_provider).map(([prov, data]) => (
                <tr key={prov}>
                  <td style={td}><code>{prov}</code></td>
                  <td style={{ ...td, textAlign: "right" }}>{data.count}</td>
                  <td style={{ ...td, textAlign: "right" }}>{data.input_tokens.toLocaleString()}</td>
                  <td style={{ ...td, textAlign: "right" }}>{data.output_tokens.toLocaleString()}</td>
                  <td style={{ ...td, textAlign: "right", color: "var(--accent)" }}>
                    {prov === "copilot" ? "Abo" : `$${data.cost_usd.toFixed(4)}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* By operation */}
      {Object.keys(s.by_operation).length > 0 && (
        <div className="card">
          <h3 style={head}>Nach Operation</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, marginTop: 10 }}>
            <thead>
              <tr style={{ color: "var(--muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1 }}>
                <th style={th}>Operation</th>
                <th style={{ ...th, textAlign: "right" }}>Aufrufe</th>
                <th style={{ ...th, textAlign: "right" }}>Kosten</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(s.by_operation).map(([op, data]) => (
                <tr key={op}>
                  <td style={td}><code>{op}</code></td>
                  <td style={{ ...td, textAlign: "right" }}>{data.count}</td>
                  <td style={{ ...td, textAlign: "right", color: "var(--accent)" }}>${data.cost_usd.toFixed(5)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Records */}
      {usage.records.length > 0 && (
        <div className="card">
          <h3 style={head}>Einzelne Aufrufe ({usage.records.length})</h3>
          <div style={{ overflowX: "auto", marginTop: 10 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ color: "var(--muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: 1 }}>
                  <th style={th}>Zeitpunkt</th>
                  <th style={th}>Provider</th>
                  <th style={th}>Operation</th>
                  <th style={{ ...th, textAlign: "right" }}>In</th>
                  <th style={{ ...th, textAlign: "right" }}>Out</th>
                  <th style={{ ...th, textAlign: "right" }}>Cache-R</th>
                  <th style={{ ...th, textAlign: "right" }}>Cache-W</th>
                  <th style={{ ...th, textAlign: "right" }}>Kosten</th>
                </tr>
              </thead>
              <tbody>
                {[...usage.records].reverse().map((r, i) => (
                  <tr key={i}>
                    <td style={{ ...td, color: "var(--muted)", fontFamily: "monospace", fontSize: 11 }}>
                      {new Date(r.ts).toLocaleString("de-DE")}
                    </td>
                    <td style={td}><code style={{ color: r.provider === "copilot" ? "#4caf50" : "var(--accent)" }}>{r.provider ?? "claude"}</code></td>
                    <td style={td}><code>{r.operation}</code></td>
                    <td style={{ ...td, textAlign: "right" }}>{r.input_tokens.toLocaleString()}</td>
                    <td style={{ ...td, textAlign: "right" }}>{r.output_tokens.toLocaleString()}</td>
                    <td style={{ ...td, textAlign: "right", color: "var(--green)" }}>
                      {r.cache_read_tokens > 0 ? r.cache_read_tokens.toLocaleString() : "—"}
                    </td>
                    <td style={{ ...td, textAlign: "right" }}>
                      {r.cache_creation_tokens > 0 ? r.cache_creation_tokens.toLocaleString() : "—"}
                    </td>
                    <td style={{ ...td, textAlign: "right", color: "var(--accent)" }}>
                      {r.provider === "copilot" ? "Abo" : `$${r.cost_usd.toFixed(5)}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {usage.records.length === 0 && (
        <p style={{ color: "var(--muted)", fontSize: 13 }}>Noch keine KI-Aufrufe aufgezeichnet.</p>
      )}
    </div>
  );
}

const head: React.CSSProperties = {
  fontSize: 12, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1,
};
const th: React.CSSProperties = {
  padding: "4px 8px", textAlign: "left", borderBottom: "1px solid var(--border)",
};
const td: React.CSSProperties = {
  padding: "5px 8px", borderBottom: "1px solid var(--border)",
};

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: accent ? "var(--accent)" : "var(--text)" }}>
        {value}
      </div>
    </div>
  );
}
