import { PatternUsage } from "../api";
import { isEmpty, locationLabel } from "../patternsViewLogic";

interface Props {
  patterns: PatternUsage[];
  onClose: () => void;
}

export default function PatternsView({ patterns, onClose }: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ fontSize: 18, fontWeight: 700 }}>◇ Verwendete Patterns</h2>
        <button onClick={onClose} style={{ fontSize: 12, padding: "3px 10px" }}>× Schließen</button>
      </div>

      {isEmpty(patterns) ? (
        <div className="card" style={{ color: "var(--muted)" }}>
          Noch keine akzeptierten Patterns. Sobald im Review Patterns akzeptiert werden,
          erscheinen sie hier mit ihren Code-Fundstellen.
        </div>
      ) : (
        patterns.map((p) => (
          <div key={p.pattern_name} className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: 15, fontWeight: 700 }}>{p.pattern_name}</h3>
              {p.refactoring_guru_url && (
                <a href={p.refactoring_guru_url} target="_blank" rel="noreferrer"
                   style={{ fontSize: 12, color: "var(--accent)" }}>
                  Refactoring Guru ↗
                </a>
              )}
            </div>

            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
              {p.specs.map((s) => (
                <span key={s.spec_id} title={s.reason}
                      style={{ fontSize: 11, padding: "2px 8px", borderRadius: 10,
                               border: "1px solid var(--border)", color: "var(--muted)" }}>
                  {s.spec_id}
                </span>
              ))}
            </div>

            <div style={{ marginTop: 10, fontSize: 13 }}>
              {p.code_locations.length === 0 ? (
                <span style={{ color: "var(--muted)" }}>Keine Code-Fundstelle gefunden.</span>
              ) : (
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {p.code_locations.map((loc, i) => (
                    <li key={i} title={loc.annotation}>
                      <code>{locationLabel(loc)}</code>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
