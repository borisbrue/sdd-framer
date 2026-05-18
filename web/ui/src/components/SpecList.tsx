import { Spec } from "../api";

interface Props {
  specs: Spec[];
  selected: string | null;
  onSelect: (specId: string) => void;
}

const SPEC_STATUS_ORDER = ["draft", "review", "approved", "in-progress", "implemented", "deprecated"];

export default function SpecList({ specs, selected, onSelect }: Props) {
  const sorted = [...specs].sort(
    (a, b) => SPEC_STATUS_ORDER.indexOf(a.status) - SPEC_STATUS_ORDER.indexOf(b.status) || a.id.localeCompare(b.id)
  );

  if (!sorted.length) {
    return <p style={{ fontSize: 12, color: "var(--muted)", padding: "8px 10px" }}>Noch keine Specs — leg eine an!</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {sorted.map(s => (
        <button
          key={s.id}
          onClick={() => onSelect(s.id)}
          style={{
            textAlign: "left", padding: "8px 10px", borderRadius: "var(--radius)",
            background: selected === s.id ? "var(--border)" : "transparent",
            border: selected === s.id ? "1px solid var(--accent)" : "1px solid transparent",
            cursor: "pointer", width: "100%",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 2 }}>
            <span style={{ fontFamily: "monospace", fontSize: 11, color: "var(--accent)" }}>{s.id}</span>
            <span className={`badge badge-${s.status}`}>{s.status}</span>
          </div>
          <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 2 }}>{s.title}</div>
          <div style={{ fontSize: 11, color: "var(--muted)", display: "flex", gap: 8 }}>
            <span>{s.contracts.length} Contracts</span>
            <span>{s.tests.length} Tests</span>
            {(!s.contracts.length || !s.tests.length) && (
              <span style={{ color: "var(--red)" }}>⚠ Lücken</span>
            )}
          </div>
        </button>
      ))}
    </div>
  );
}
