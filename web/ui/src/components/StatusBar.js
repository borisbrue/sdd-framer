import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { api } from "../api";
export default function StatusBar({ onShowAiUsage, onShowSettings, onShowServerInfo }) {
    const [status, setStatus] = useState(null);
    const [validating, setValidating] = useState(false);
    const [result, setResult] = useState(null);
    useEffect(() => {
        api.getStatus().then(setStatus).catch(console.error);
    }, []);
    async function handleValidate() {
        setValidating(true);
        setResult(null);
        try {
            const r = await api.validate();
            setResult(r);
            const s = await api.getStatus();
            setStatus(s);
        }
        finally {
            setValidating(false);
        }
    }
    async function handleTrace() {
        await api.trace();
        alert("Traceability-Matrix aktualisiert.");
    }
    return (_jsxs("div", { style: { borderBottom: "1px solid var(--border)", background: "var(--surface)", padding: "10px 20px", display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap" }, children: [_jsx("span", { style: { fontWeight: 700, color: "var(--accent)", fontSize: 16 }, children: "SDD Framer" }), status && (_jsxs(_Fragment, { children: [_jsx(Stat, { label: "Specs", value: status.specs }), _jsx(Stat, { label: "Contracts", value: status.contracts }), _jsx(Stat, { label: "Tests", value: status.tests }), _jsx("span", { className: status.gaps > 0 ? "gap" : "ok", children: status.gaps > 0 ? `⚠ ${status.gaps} Lücken` : "✓ vollständig" })] })), _jsxs("div", { style: { marginLeft: "auto", display: "flex", gap: 8 }, children: [_jsx("button", { onClick: handleValidate, disabled: validating, children: validating ? "…" : "▶ Validate" }), _jsx("button", { onClick: handleTrace, children: "\u21BB Trace" }), _jsx("button", { onClick: onShowAiUsage, style: { color: "var(--accent)", borderColor: "var(--accent)" }, children: "\u2726 KI-Kosten" }), _jsx("button", { onClick: onShowServerInfo, style: { color: "var(--muted)", borderColor: "var(--border)" }, children: "\u2B1B QR" }), _jsx("button", { onClick: onShowSettings, style: { color: "var(--muted)", borderColor: "var(--border)" }, children: "\u2699 Einstellungen" })] }), result && (_jsx("div", { style: { width: "100%", marginTop: 6 }, children: result.ok && !result.warnings.length
                    ? _jsx("span", { className: "ok", children: "\u2713 Alles in Ordnung" })
                    : (_jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 3 }, children: [result.errors.map((e, i) => (_jsxs("span", { className: "gap", children: ["\u2717 ", e.file, ": ", e.message] }, i))), result.warnings.map((w, i) => (_jsxs("span", { style: { color: "var(--yellow)" }, children: ["\u26A0 ", w.file, ": ", w.message] }, i)))] })) }))] }));
}
function Stat({ label, value }) {
    return (_jsxs("span", { style: { color: "var(--muted)", fontSize: 13 }, children: [label, ": ", _jsx("strong", { style: { color: "var(--text)" }, children: value })] }));
}
