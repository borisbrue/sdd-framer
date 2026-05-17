import { useState } from "react";
import { Project, Spec } from "../api";

interface Props {
  projects: Project[];
  specs: Spec[];
  selected: string | null;
  onSelect: (specId: string) => void;
}

const STATUS_COLORS: Record<string, string> = {
  active:   "var(--green)",
  planning: "var(--yellow)",
  archived: "var(--muted)",
};

const SPEC_STATUS_ORDER = ["draft", "review", "approved", "implemented", "deprecated"];

export default function ProjectList({ projects, specs, selected, onSelect }: Props) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  function toggle(id: string) {
    setCollapsed(prev => ({ ...prev, [id]: !prev[id] }));
  }

  // Group specs by project, collect unassigned separately
  const byProject = new Map<string, Spec[]>(projects.map(p => [p.id, []]));
  const unassigned: Spec[] = [];

  for (const s of specs) {
    if (s.project && byProject.has(s.project)) {
      byProject.get(s.project)!.push(s);
    } else {
      unassigned.push(s);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {projects.map(p => {
        const pSpecs = (byProject.get(p.id) ?? []).sort(
          (a, b) => SPEC_STATUS_ORDER.indexOf(a.status) - SPEC_STATUS_ORDER.indexOf(b.status) || a.id.localeCompare(b.id)
        );
        const isOpen = !collapsed[p.id];
        const statusColor = STATUS_COLORS[p.status] ?? "var(--muted)";
        const hasGap = pSpecs.some(s => !s.contracts.length || !s.tests.length);

        return (
          <div key={p.id}>
            {/* Project header */}
            <button
              onClick={() => toggle(p.id)}
              style={{
                width: "100%", textAlign: "left", padding: "8px 10px",
                background: "var(--surface)", border: "1px solid var(--border)",
                borderRadius: "var(--radius)", cursor: "pointer",
                display: "flex", alignItems: "center", gap: 8,
              }}
            >
              <span style={{ fontSize: 10, color: "var(--muted)", width: 10 }}>
                {isOpen ? "▼" : "▶"}
              </span>
              <span style={{ fontFamily: "monospace", fontSize: 11, color: "var(--muted)", flexShrink: 0 }}>
                {p.id}
              </span>
              <span style={{ fontSize: 13, fontWeight: 600, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {p.name}
              </span>
              <span style={{ fontSize: 10, color: statusColor, border: `1px solid ${statusColor}`, padding: "1px 5px", borderRadius: 999, flexShrink: 0 }}>
                {p.status}
              </span>
              {hasGap && <span style={{ fontSize: 10, color: "var(--red)" }}>⚠</span>}
            </button>

            {/* Spec list */}
            {isOpen && (
              <div style={{ paddingLeft: 12, marginTop: 2, display: "flex", flexDirection: "column", gap: 2 }}>
                {pSpecs.length === 0
                  ? <p style={{ fontSize: 12, color: "var(--muted)", padding: "6px 8px" }}>Keine Specs</p>
                  : pSpecs.map(s => <SpecRow key={s.id} spec={s} selected={selected === s.id} onSelect={onSelect} />)
                }
              </div>
            )}
          </div>
        );
      })}

      {/* Unassigned specs */}
      {unassigned.length > 0 && (
        <div>
          <div style={{ padding: "6px 10px 4px", fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1 }}>
            Kein Projekt
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {unassigned
              .sort((a, b) => SPEC_STATUS_ORDER.indexOf(a.status) - SPEC_STATUS_ORDER.indexOf(b.status) || a.id.localeCompare(b.id))
              .map(s => <SpecRow key={s.id} spec={s} selected={selected === s.id} onSelect={onSelect} />)
            }
          </div>
        </div>
      )}
    </div>
  );
}

function SpecRow({ spec: s, selected, onSelect }: { spec: Spec; selected: boolean; onSelect: (id: string) => void }) {
  return (
    <button
      key={s.id}
      onClick={() => onSelect(s.id)}
      style={{
        textAlign: "left", padding: "8px 10px", borderRadius: "var(--radius)",
        background: selected ? "var(--border)" : "transparent",
        border: selected ? "1px solid var(--accent)" : "1px solid transparent",
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
  );
}
