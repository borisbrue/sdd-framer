import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
const SPEC_STATUS_ORDER = ["draft", "review", "approved", "in-progress", "implemented", "deprecated"];
export default function SpecList({ specs, selected, onSelect }) {
    const sorted = [...specs].sort((a, b) => SPEC_STATUS_ORDER.indexOf(a.status) - SPEC_STATUS_ORDER.indexOf(b.status) || a.id.localeCompare(b.id));
    if (!sorted.length) {
        return _jsx("p", { style: { fontSize: 12, color: "var(--muted)", padding: "8px 10px" }, children: "Noch keine Specs \u2014 leg eine an!" });
    }
    return (_jsx("div", { style: { display: "flex", flexDirection: "column", gap: 2 }, children: sorted.map(s => (_jsxs("button", { onClick: () => onSelect(s.id), style: {
                textAlign: "left", padding: "8px 10px", borderRadius: "var(--radius)",
                background: selected === s.id ? "var(--border)" : "transparent",
                border: selected === s.id ? "1px solid var(--accent)" : "1px solid transparent",
                cursor: "pointer", width: "100%",
            }, children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 2 }, children: [_jsx("span", { style: { fontFamily: "monospace", fontSize: 11, color: "var(--accent)" }, children: s.id }), _jsx("span", { className: `badge badge-${s.status}`, children: s.status })] }), _jsx("div", { style: { fontSize: 13, fontWeight: 500, marginBottom: 2 }, children: s.title }), _jsxs("div", { style: { fontSize: 11, color: "var(--muted)", display: "flex", gap: 8 }, children: [_jsxs("span", { children: [s.contracts.length, " Contracts"] }), _jsxs("span", { children: [s.tests.length, " Tests"] }), (!s.contracts.length || !s.tests.length) && (_jsx("span", { style: { color: "var(--red)" }, children: "\u26A0 L\u00FCcken" }))] })] }, s.id))) }));
}
