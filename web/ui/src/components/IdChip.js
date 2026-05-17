import { jsxs as _jsxs } from "react/jsx-runtime";
export default function IdChip({ id, onClick, missing = false }) {
    const prefix = id.split("-")[0];
    const colors = {
        SPEC: "var(--accent)",
        CON: "var(--green)",
        TST: "#cba6f7",
        ADR: "var(--yellow)",
    };
    const color = colors[prefix] ?? "var(--muted)";
    return (_jsxs("span", { onClick: () => onClick(id), style: {
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
        }, title: missing ? "Referenz fehlt" : `Zu ${id} navigieren`, children: [id, missing && " ⚠"] }));
}
