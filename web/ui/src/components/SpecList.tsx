import { Spec } from "../api";

interface Props {
  specs: Spec[];
  selected: string | null;
  onSelect: (id: string) => void;
}

const STATUS_ORDER = ["draft", "review", "approved", "implemented", "deprecated"];

export default function SpecList({ specs, selected, onSelect }: Props) {
  const sorted = [...specs].sort((a, b) =>
    STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status) ||
    a.id.localeCompare(b.id)
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {sorted.map((s) => (
        <button
          key={s.id}
          onClick={() => onSelect(s.id)}
          style={{
            textAlign: "left",
            padding: "10px 12px",
            borderRadius: "var(--radius)",
            background: selected === s.id ? "var(--border)" : "transparent",
            border: selected === s.id ? "1px solid var(--accent)" : "1px solid transparent",
            cursor: "pointer",
            width: "100%",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
            <span style={{ fontFamily: "monospace", fontSize: 12, color: "var(--accent)" }}>{s.id}</span>
            <Badge status={s.status} />
          </div>
          <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>{s.title}</div>
          <div style={{ fontSize: 11, color: "var(--muted)", display: "flex", gap: 10 }}>
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

function Badge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}
