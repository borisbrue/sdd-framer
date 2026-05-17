import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { api } from "../api";
import AnalyzePanel from "./AnalyzePanel";
import IdChip from "./IdChip";
import MarkdownBody from "./MarkdownBody";
import OpenButton from "./OpenButton";
export default function ContractDetail({ contractId, onNavigate }) {
    const [detail, setDetail] = useState(null);
    useEffect(() => {
        setDetail(null);
        api.getContract(contractId).then(setDetail).catch(console.error);
    }, [contractId]);
    if (!detail)
        return _jsx("div", { style: { padding: 20, color: "var(--muted)" }, children: "Lade\u2026" });
    return (_jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 20 }, children: [_jsxs("div", { className: "card", children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }, children: [_jsxs("div", { style: { flex: 1 }, children: [_jsxs("div", { style: { display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }, children: [_jsx("code", { style: { color: "var(--green)", fontSize: 13 }, children: detail.id }), _jsx("span", { className: `badge badge-${detail.status}`, children: detail.status }), _jsxs("code", { style: { fontSize: 11, color: "var(--muted)" }, children: ["[", detail.format, "]"] })] }), _jsx("h2", { style: { fontSize: 20, fontWeight: 700, marginBottom: 8 }, children: detail.title }), _jsxs("div", { style: { display: "flex", gap: 12, fontSize: 12, color: "var(--muted)", flexWrap: "wrap" }, children: [_jsxs("span", { children: ["Spec: ", _jsx(IdChip, { id: detail.spec, onClick: onNavigate })] }), detail.version && _jsxs("span", { children: ["v", detail.version] })] })] }), _jsx("div", { style: { display: "flex", gap: 8, flexShrink: 0 }, children: _jsx(OpenButton, { absFile: detail.abs_file }) })] }), _jsx("div", { style: { marginTop: 10, fontSize: 11, color: "var(--muted)" }, children: _jsx("code", { children: detail.file }) })] }), detail.tests.length > 0 && (_jsxs("section", { className: "card", children: [_jsx("h3", { style: sectionHead, children: "Tests" }), _jsx("div", { style: { display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }, children: detail.tests.map(id => _jsx(IdChip, { id: id, onClick: onNavigate }, id)) })] })), detail.artifact_content && (_jsxs("section", { className: "card", children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }, children: [_jsxs("h3", { style: sectionHead, children: ["Artifact: ", _jsx("code", { style: { color: "var(--accent)" }, children: detail.artifact })] }), _jsx(OpenButton, { absFile: detail.abs_artifact, label: "Artifact \u00F6ffnen" })] }), _jsx("pre", { style: { background: "var(--bg)", borderRadius: 6, padding: 12, fontSize: 12, overflowX: "auto", whiteSpace: "pre-wrap", wordBreak: "break-word" }, children: detail.artifact_content })] })), detail.body.trim() && (_jsxs("section", { className: "card", children: [_jsx("h3", { style: { ...sectionHead, marginBottom: 12 }, children: "Inhalt" }), _jsx(MarkdownBody, { markdown: detail.body, onIdClick: onNavigate })] })), _jsx(AnalyzePanel, { docId: detail.id, docContent: detail.body, docType: "contract" })] }));
}
const sectionHead = {
    fontSize: 12,
    color: "var(--muted)",
    textTransform: "uppercase",
    letterSpacing: 1,
};
