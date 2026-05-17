import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
const STATUS_COLORS = {
    active: "var(--green)",
    planning: "var(--yellow)",
    archived: "var(--muted)",
};
const SPEC_STATUS_ORDER = ["draft", "review", "approved", "implemented", "deprecated"];
export default function ProjectList({ projects, specs, selected, onSelect }) {
    const [collapsed, setCollapsed] = useState({});
    function toggle(id) {
        setCollapsed(prev => ({ ...prev, [id]: !prev[id] }));
    }
    // Group specs by project, collect unassigned separately
    const byProject = new Map(projects.map(p => [p.id, []]));
    const unassigned = [];
    for (const s of specs) {
        if (s.project && byProject.has(s.project)) {
            byProject.get(s.project).push(s);
        }
        else {
            unassigned.push(s);
        }
    }
    return (_jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 2 }, children: [projects.map(p => {
                const pSpecs = (byProject.get(p.id) ?? []).sort((a, b) => SPEC_STATUS_ORDER.indexOf(a.status) - SPEC_STATUS_ORDER.indexOf(b.status) || a.id.localeCompare(b.id));
                const isOpen = !collapsed[p.id];
                const statusColor = STATUS_COLORS[p.status] ?? "var(--muted)";
                const hasGap = pSpecs.some(s => !s.contracts.length || !s.tests.length);
                return (_jsxs("div", { children: [_jsxs("button", { onClick: () => toggle(p.id), style: {
                                width: "100%", textAlign: "left", padding: "8px 10px",
                                background: "var(--surface)", border: "1px solid var(--border)",
                                borderRadius: "var(--radius)", cursor: "pointer",
                                display: "flex", alignItems: "center", gap: 8,
                            }, children: [_jsx("span", { style: { fontSize: 10, color: "var(--muted)", width: 10 }, children: isOpen ? "▼" : "▶" }), _jsx("span", { style: { fontFamily: "monospace", fontSize: 11, color: "var(--muted)", flexShrink: 0 }, children: p.id }), _jsx("span", { style: { fontSize: 13, fontWeight: 600, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }, children: p.name }), _jsx("span", { style: { fontSize: 10, color: statusColor, border: `1px solid ${statusColor}`, padding: "1px 5px", borderRadius: 999, flexShrink: 0 }, children: p.status }), hasGap && _jsx("span", { style: { fontSize: 10, color: "var(--red)" }, children: "\u26A0" })] }), isOpen && (_jsx("div", { style: { paddingLeft: 12, marginTop: 2, display: "flex", flexDirection: "column", gap: 2 }, children: pSpecs.length === 0
                                ? _jsx("p", { style: { fontSize: 12, color: "var(--muted)", padding: "6px 8px" }, children: "Keine Specs" })
                                : pSpecs.map(s => _jsx(SpecRow, { spec: s, selected: selected === s.id, onSelect: onSelect }, s.id)) }))] }, p.id));
            }), unassigned.length > 0 && (_jsxs("div", { children: [_jsx("div", { style: { padding: "6px 10px 4px", fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1 }, children: "Kein Projekt" }), _jsx("div", { style: { display: "flex", flexDirection: "column", gap: 2 }, children: unassigned
                            .sort((a, b) => SPEC_STATUS_ORDER.indexOf(a.status) - SPEC_STATUS_ORDER.indexOf(b.status) || a.id.localeCompare(b.id))
                            .map(s => _jsx(SpecRow, { spec: s, selected: selected === s.id, onSelect: onSelect }, s.id)) })] }))] }));
}
function SpecRow({ spec: s, selected, onSelect }) {
    return (_jsxs("button", { onClick: () => onSelect(s.id), style: {
            textAlign: "left", padding: "8px 10px", borderRadius: "var(--radius)",
            background: selected ? "var(--border)" : "transparent",
            border: selected ? "1px solid var(--accent)" : "1px solid transparent",
            cursor: "pointer", width: "100%",
        }, children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 2 }, children: [_jsx("span", { style: { fontFamily: "monospace", fontSize: 11, color: "var(--accent)" }, children: s.id }), _jsx("span", { className: `badge badge-${s.status}`, children: s.status })] }), _jsx("div", { style: { fontSize: 13, fontWeight: 500, marginBottom: 2 }, children: s.title }), _jsxs("div", { style: { fontSize: 11, color: "var(--muted)", display: "flex", gap: 8 }, children: [_jsxs("span", { children: [s.contracts.length, " Contracts"] }), _jsxs("span", { children: [s.tests.length, " Tests"] }), (!s.contracts.length || !s.tests.length) && (_jsx("span", { style: { color: "var(--red)" }, children: "\u26A0 L\u00FCcken" }))] })] }, s.id));
}
