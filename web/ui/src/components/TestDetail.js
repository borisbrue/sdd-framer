import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { api } from "../api";
import IdChip from "./IdChip";
import MarkdownBody from "./MarkdownBody";
import OpenButton from "./OpenButton";
const LEVEL_COLORS = {
    unit: "#cba6f7",
    integration: "#89dceb",
    contract: "var(--green)",
    acceptance: "var(--accent)",
    performance: "var(--yellow)",
    property: "#f5c2e7",
};
export default function TestDetail({ testId, onNavigate }) {
    const [detail, setDetail] = useState(null);
    useEffect(() => {
        setDetail(null);
        api.getTest(testId).then(setDetail).catch(console.error);
    }, [testId]);
    if (!detail)
        return _jsx("div", { style: { padding: 20, color: "var(--muted)" }, children: "Lade\u2026" });
    const levelColor = LEVEL_COLORS[detail.level] ?? "var(--muted)";
    return (_jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 20 }, children: [_jsxs("div", { className: "card", children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }, children: [_jsxs("div", { style: { flex: 1 }, children: [_jsxs("div", { style: { display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }, children: [_jsx("code", { style: { color: "#cba6f7", fontSize: 13 }, children: detail.id }), _jsx("span", { className: `badge badge-${detail.status}`, children: detail.status }), _jsx("span", { style: { fontSize: 11, color: levelColor, border: `1px solid ${levelColor}`, padding: "1px 8px", borderRadius: 999 }, children: detail.level })] }), _jsx("h2", { style: { fontSize: 20, fontWeight: 700, marginBottom: 8 }, children: detail.title }), _jsxs("div", { style: { display: "flex", gap: 12, fontSize: 12, color: "var(--muted)", flexWrap: "wrap", alignItems: "center" }, children: [_jsxs("span", { children: ["Spec: ", _jsx(IdChip, { id: detail.spec, onClick: onNavigate })] }), _jsxs("span", { children: ["Contract: ", _jsx(IdChip, { id: detail.contract, onClick: onNavigate })] }), detail.framework && _jsxs("span", { children: ["Framework: ", _jsx("strong", { style: { color: "var(--text)" }, children: detail.framework })] }), detail.version && _jsxs("span", { children: ["v", detail.version] })] })] }), _jsx("div", { style: { display: "flex", gap: 8, flexShrink: 0 }, children: _jsx(OpenButton, { absFile: detail.abs_file }) })] }), _jsx("div", { style: { marginTop: 10, fontSize: 11, color: "var(--muted)" }, children: _jsx("code", { children: detail.file }) })] }), detail.body.trim() && (_jsxs("section", { className: "card", children: [_jsx("h3", { style: { fontSize: 12, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 12 }, children: "Inhalt" }), _jsx(MarkdownBody, { markdown: detail.body, onIdClick: onNavigate })] }))] }));
}
