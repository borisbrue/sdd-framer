import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
import { useState } from "react";
import { api } from "../api";
import MarkdownBody from "./MarkdownBody";
const PROVIDER_LABEL = {
    claude: "Claude (Anthropic)",
    copilot: "GitHub Copilot",
};
function UsagePill({ entry }) {
    const cached = entry.cache_read_tokens > 0;
    const isCopilot = entry.provider === "copilot";
    return (_jsxs("span", { style: { fontSize: 10, color: "var(--muted)", fontFamily: "monospace" }, children: [entry.input_tokens, "\u2191 ", entry.output_tokens, "\u2193", cached && _jsxs("span", { style: { color: "var(--green)" }, children: [" ", entry.cache_read_tokens, " cached"] }), isCopilot
                ? _jsx("span", { style: { color: "var(--muted)" }, children: " (Abo)" })
                : _jsxs("span", { children: [" $", entry.cost_usd.toFixed(5)] })] }));
}
export default function AiPanel({ specId, specContent, onApply, onNavigate }) {
    const [open, setOpen] = useState(false);
    const [provider, setProvider] = useState("claude");
    const [mode, setMode] = useState("idle");
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState("");
    const [usage, setUsage] = useState(null);
    const [error, setError] = useState("");
    const [instructions, setInstructions] = useState("");
    async function run(op) {
        setLoading(true);
        setError("");
        setResult("");
        setUsage(null);
        try {
            let res;
            if (op === "improve") {
                const payload = { spec_id: specId, current_content: specContent, instructions };
                res = provider === "copilot"
                    ? await api.copilotImproveSpec(payload)
                    : await api.aiImproveSpec(payload);
            }
            else {
                const payload = { spec_id: specId, spec_content: specContent };
                res = provider === "copilot"
                    ? await api.copilotSuggestContracts(payload)
                    : await api.aiSuggestContracts(payload);
            }
            setResult(res.result);
            setUsage(res.usage);
        }
        catch (e) {
            setError(e instanceof Error ? e.message : "Fehler");
        }
        finally {
            setLoading(false);
        }
    }
    if (!open) {
        return (_jsx("button", { onClick: () => setOpen(true), style: { fontSize: 12, padding: "4px 12px", color: "var(--accent)", borderColor: "var(--accent)" }, children: "\u2726 KI-Assistent" }));
    }
    const accentColor = provider === "copilot" ? "#4caf50" : "var(--accent)";
    return (_jsxs("section", { className: "card", style: { borderColor: accentColor }, children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }, children: [_jsx("h3", { style: { fontSize: 12, color: accentColor, textTransform: "uppercase", letterSpacing: 1 }, children: "\u2726 KI-Assistent" }), _jsx("button", { onClick: () => setOpen(false), style: { fontSize: 12, padding: "2px 8px" }, children: "\u00D7" })] }), _jsx("div", { style: { display: "flex", gap: 4, marginBottom: 12, background: "var(--bg)", borderRadius: 6, padding: 3 }, children: ["claude", "copilot"].map(p => (_jsx("button", { onClick: () => { setProvider(p); setResult(""); setUsage(null); setError(""); }, style: {
                        flex: 1,
                        fontSize: 11,
                        padding: "4px 8px",
                        background: provider === p ? (p === "copilot" ? "#4caf50" : "var(--accent)") : "transparent",
                        color: provider === p ? "#1e1e2e" : "var(--muted)",
                        border: "none",
                        borderRadius: 4,
                        cursor: "pointer",
                    }, children: PROVIDER_LABEL[p] }, p))) }), _jsxs("div", { style: { display: "flex", gap: 8, marginBottom: 12 }, children: [_jsx("button", { onClick: () => setMode(mode === "improve" ? "idle" : "improve"), style: { fontSize: 12, padding: "4px 12px", ...(mode === "improve" ? { background: accentColor, color: "#1e1e2e" } : {}) }, children: "Spec verbessern" }), _jsx("button", { onClick: () => { setMode("suggest"); run("suggest"); }, style: { fontSize: 12, padding: "4px 12px", ...(mode === "suggest" ? { background: accentColor, color: "#1e1e2e" } : {}) }, disabled: loading, children: "Contracts vorschlagen" })] }), mode === "improve" && (_jsxs("div", { style: { marginBottom: 12 }, children: [_jsx("textarea", { value: instructions, onChange: e => setInstructions(e.target.value), placeholder: "Anweisungen, z.B. 'F\u00FCge Akzeptanzkriterien hinzu' oder 'K\u00FCrze den Text'", style: { width: "100%", minHeight: 70, fontSize: 12, padding: 8, boxSizing: "border-box", background: "var(--bg)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: 4, resize: "vertical" } }), _jsx("div", { style: { display: "flex", gap: 8, marginTop: 8 }, children: _jsx("button", { className: "primary", onClick: () => run("improve"), disabled: loading || !instructions.trim(), style: { fontSize: 12, padding: "4px 12px" }, children: loading ? "…" : "Ausführen" }) })] })), loading && (_jsx("p", { style: { color: "var(--muted)", fontSize: 13 }, children: provider === "copilot" ? "GitHub Copilot denkt nach…" : "Claude denkt nach…" })), error && _jsx("p", { style: { color: "var(--red)", fontSize: 13 }, children: error }), result && (_jsxs("div", { children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }, children: [_jsx("span", { style: { fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1 }, children: "Ergebnis" }), _jsxs("div", { style: { display: "flex", gap: 8, alignItems: "center" }, children: [usage && _jsx(UsagePill, { entry: usage }), onApply && mode === "improve" && (_jsx("button", { className: "primary", onClick: () => onApply(result), style: { fontSize: 11, padding: "2px 10px" }, children: "\u00DCbernehmen" }))] })] }), _jsx("div", { style: { background: "var(--bg)", borderRadius: 6, padding: 12, fontSize: 13 }, children: _jsx(MarkdownBody, { markdown: result, onIdClick: onNavigate }) })] }))] }));
}
