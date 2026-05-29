import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { api } from "../api";
import AiPanel from "./AiPanel";
import AnalyzePanel from "./AnalyzePanel";
import ApprovePanel from "./ApprovePanel";
import RestructurePanel from "./RestructurePanel";
import ExecutePanel from "./ExecutePanel";
import LogPanel from "./LogPanel";
import TestRunPanel from "./TestRunPanel";
import ContractForm from "./ContractForm";
import IdChip from "./IdChip";
import MarkdownBody from "./MarkdownBody";
import OpenButton from "./OpenButton";
import SpecPipelineView from "./SpecPipelineView";
import TestForm from "./TestForm";
export default function SpecDetail({ specId, contracts, tests, onNavigate, onRefresh }) {
    const [detail, setDetail] = useState(null);
    const [showContractForm, setShowContractForm] = useState(false);
    const [showTestForm, setShowTestForm] = useState(false);
    const [holdouts, setHoldouts] = useState([]);
    const [analysisTrigger, setAnalysisTrigger] = useState(0);
    const [logConnectTrigger, setLogConnectTrigger] = useState(0);
    useEffect(() => {
        setDetail(null);
        api.getSpec(specId).then(setDetail).catch(console.error);
        api.getHoldouts(specId).then(d => setHoldouts(d.holdouts)).catch(() => setHoldouts([]));
    }, [specId]);
    if (!detail)
        return _jsx("div", { style: { padding: 20, color: "var(--muted)" }, children: "Lade\u2026" });
    const myContracts = contracts.filter((c) => c.spec === specId);
    const myTests = tests.filter((t) => t.spec === specId);
    return (_jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 20 }, children: [_jsx(ExecutePanel, { spec: detail, onStatusChange: () => {
                    api.getSpec(specId).then(setDetail).catch(console.error);
                    onRefresh();
                } }), _jsxs("div", { className: "card", children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }, children: [_jsxs("div", { style: { flex: 1 }, children: [_jsxs("div", { style: { display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }, children: [_jsx("code", { style: { color: "var(--accent)", fontSize: 13 }, children: detail.id }), _jsxs("select", { value: detail.status, onChange: async (e) => {
                                                    const s = e.target.value;
                                                    if (s === "approved")
                                                        return;
                                                    await api.patchSpecStatus(detail.id, s);
                                                    setDetail(d => d ? { ...d, status: s } : d);
                                                    onRefresh();
                                                }, style: {
                                                    fontSize: 11, background: "var(--surface)", color: "var(--muted)",
                                                    border: "1px solid var(--border)", borderRadius: 4, padding: "2px 6px", cursor: "pointer",
                                                }, children: [_jsx("option", { value: "draft", children: "draft" }), _jsx("option", { value: "active", children: "active" }), _jsx("option", { value: "review", children: "review" }), _jsx("option", { value: "approved", disabled: true, children: "approved (nur via Gate)" }), _jsx("option", { value: "deprecated", children: "deprecated" })] }), detail.priority !== "medium" && (_jsx("span", { style: { fontSize: 11, color: "var(--yellow)" }, children: detail.priority }))] }), _jsx("h2", { style: { fontSize: 20, fontWeight: 700, marginBottom: 8 }, children: detail.title }), _jsxs("div", { style: { display: "flex", gap: 16, fontSize: 12, color: "var(--muted)", flexWrap: "wrap" }, children: [detail.owner && _jsxs("span", { children: ["Owner: ", _jsx("strong", { style: { color: "var(--text)" }, children: detail.owner })] }), detail.version && _jsxs("span", { children: ["v", detail.version] }), detail.created && _jsxs("span", { children: ["Erstellt: ", detail.created] }), detail.tags.length > 0 && (_jsx("span", { children: detail.tags.map(t => _jsx("code", { style: { marginLeft: 4, background: "var(--surface)", padding: "1px 5px", borderRadius: 4 }, children: t }, t)) }))] })] }), _jsx("div", { style: { display: "flex", gap: 8, flexShrink: 0 }, children: _jsx(OpenButton, { absFile: detail.abs_file }) })] }), _jsx("div", { style: { marginTop: 10, fontSize: 11, color: "var(--muted)" }, children: _jsx("code", { children: detail.file }) })] }), _jsx(SpecPipelineView, { specId: specId, onActionTriggered: () => setLogConnectTrigger(k => k + 1) }), (detail.depends_on.length > 0) && (_jsxs("section", { className: "card", children: [_jsx("h3", { style: sectionHead, children: "H\u00E4ngt ab von" }), _jsx("div", { style: { display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }, children: detail.depends_on.map(id => _jsx(IdChip, { id: id, onClick: onNavigate }, id)) })] })), _jsxs("section", { children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }, children: [_jsxs("h3", { style: sectionHead, children: ["Contracts (", myContracts.length, ")"] }), _jsx("button", { onClick: () => setShowContractForm(v => !v), children: "+ Contract" })] }), showContractForm && (_jsx(ContractForm, { specId: specId, onCreated: () => { setShowContractForm(false); onRefresh(); }, onCancel: () => setShowContractForm(false) })), myContracts.length === 0 && !showContractForm
                        ? _jsx("p", { style: { color: "var(--red)", fontSize: 13 }, children: "\u26A0 Kein Contract \u2013 Spec kann nicht validiert werden." })
                        : (_jsx("div", { style: { display: "flex", flexDirection: "column", gap: 6 }, children: myContracts.map(c => (_jsxs("div", { className: "card", style: { cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }, onClick: () => onNavigate(c.id), children: [_jsxs("div", { style: { display: "flex", alignItems: "center", gap: 10 }, children: [_jsx(IdChip, { id: c.id, onClick: onNavigate }), _jsx("span", { style: { fontSize: 13 }, children: c.title }), _jsxs("code", { style: { fontSize: 11, color: "var(--muted)" }, children: ["[", c.format, "]"] })] }), _jsxs("div", { style: { display: "flex", alignItems: "center", gap: 8 }, children: [_jsxs("span", { style: { fontSize: 11, color: "var(--muted)" }, children: [c.tests.length, " Tests"] }), _jsx(OpenButton, { absFile: c.abs_file, label: "\u2197" })] })] }, c.id))) }))] }), _jsxs("section", { children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }, children: [_jsxs("h3", { style: sectionHead, children: ["Tests (", myTests.length, ")"] }), _jsx("button", { onClick: () => setShowTestForm(v => !v), disabled: myContracts.length === 0, children: "+ Test" })] }), showTestForm && (_jsx(TestForm, { specId: specId, contracts: myContracts, onCreated: () => { setShowTestForm(false); onRefresh(); }, onCancel: () => setShowTestForm(false) })), myTests.length === 0 && !showTestForm
                        ? _jsx("p", { style: { color: "var(--red)", fontSize: 13 }, children: "\u26A0 Kein Test angelegt." })
                        : (_jsx("div", { style: { display: "flex", flexDirection: "column", gap: 6 }, children: myTests.map(t => (_jsxs("div", { className: "card", style: { cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }, onClick: () => onNavigate(t.id), children: [_jsxs("div", { style: { display: "flex", alignItems: "center", gap: 10 }, children: [_jsx(IdChip, { id: t.id, onClick: onNavigate }), _jsx("span", { style: { fontSize: 13 }, children: t.title })] }), _jsxs("div", { style: { display: "flex", alignItems: "center", gap: 8 }, children: [_jsx("span", { style: { fontSize: 11, color: "var(--muted)" }, children: t.level }), _jsx(OpenButton, { absFile: t.abs_file, label: "\u2197" })] })] }, t.id))) }))] }), holdouts.length > 0 && (_jsxs("section", { children: [_jsxs("h3", { style: { ...sectionHead, marginBottom: 8 }, children: ["Holdout-Szenarien (", holdouts.length, ")"] }), _jsx("div", { style: { display: "flex", flexDirection: "column", gap: 6 }, children: holdouts.map(h => (_jsxs("div", { className: "card", style: { cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }, onClick: () => onNavigate(h.id), children: [_jsxs("div", { style: { display: "flex", alignItems: "center", gap: 10 }, children: [_jsx(IdChip, { id: h.id, onClick: onNavigate }), _jsx("span", { style: { fontSize: 13 }, children: h.title })] }), _jsxs("div", { style: { display: "flex", alignItems: "center", gap: 8 }, children: [_jsx("span", { style: { fontSize: 11, color: "var(--muted)" }, children: h.status }), _jsx(OpenButton, { absFile: h.abs_file, label: "\u2197" })] })] }, h.id))) })] })), _jsx(TestRunPanel, { specId: specId }), _jsx(LogPanel, { specId: specId, autoConnectTrigger: logConnectTrigger }), detail.body.trim() && (_jsxs("section", { className: "card", children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }, children: [_jsx("h3", { style: sectionHead, children: "Inhalt" }), _jsx(RestructurePanel, { docId: detail.id, docType: "spec", docContent: detail.body, onRestructured: (newBody) => {
                                    setDetail(d => d ? { ...d, body: newBody } : d);
                                    setAnalysisTrigger(k => k + 1);
                                } })] }), _jsx(MarkdownBody, { markdown: detail.body, onIdClick: onNavigate })] })), (detail.status === "review" || detail.status === "approved") && (_jsx(ApprovePanel, { specId: detail.id, onApproved: () => {
                    setDetail(d => d ? { ...d, status: "approved" } : d);
                    onRefresh();
                } })), _jsx(AnalyzePanel, { docId: detail.id, docContent: detail.body, docType: "spec", forceStartKey: analysisTrigger }), _jsx(AiPanel, { specId: detail.id, specContent: detail.body, onNavigate: onNavigate })] }));
}
const sectionHead = {
    fontSize: 12,
    color: "var(--muted)",
    textTransform: "uppercase",
    letterSpacing: 1,
};
