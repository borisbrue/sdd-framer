interface Props {
  id: string;
  onClick: (id: string) => void;
  missing?: boolean;
}

export default function IdChip({ id, onClick, missing = false }: Props) {
  const prefix = id.split("-")[0] as "SPEC" | "CON" | "TST" | "ADR";
  const colors: Record<string, string> = {
    SPEC: "var(--accent)",
    CON:  "var(--green)",
    TST:  "#cba6f7",
    ADR:  "var(--yellow)",
  };
  const color = colors[prefix] ?? "var(--muted)";

  return (
    <span
      onClick={() => onClick(id)}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "2px 8px",
        borderRadius: 999,
        background: "var(--surface)",
        border: `1px solid ${missing ? "var(--red)" : color}`,
        color: missing ? "var(--red)" : color,
        fontFamily: "monospace",
        fontSize: 12,
        cursor: "pointer",
        userSelect: "none",
      }}
      title={missing ? "Referenz fehlt" : `Zu ${id} navigieren`}
    >
      {id}
      {missing && " ⚠"}
    </span>
  );
}
