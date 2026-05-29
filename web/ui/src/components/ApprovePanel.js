import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { api } from "../api";
export default function ApprovePanel({ specId, onApproved }) {
    const [running, setRunning] = useState(false);
    const [checks, setChecks] = useState(null);
    const [approved, setApproved] = useState(false);
    const [error, setError] = useState("");
    async function handleCheck() {
        setRunning(true);
        setError("");
        setChecks(null);
        setApproved(false);
        try {
            const result = await api.approveSpec(specId);
            setChecks(result.checks);
            setApproved(result.approved);
            if (result.approved)
                onApproved();
        }
        catch (e) {
            setError(e instanceof Error ? e.message : "Gate-Prüfung fehlgeschlagen.");
        }
        finally {
            setRunning(false);
        }
    }
    const allPassed = checks?.every(c => c.passed) ?? false;
    return (_jsxs("section", { className: "card", style: { borderColor: approved ? "var(--green)" : "var(--accent)" }, children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }, children: [_jsx("h3", { style: { fontSize: 12, color: approved ? "var(--green)" : "var(--accent)", textTransform: "uppercase", letterSpacing: 1 }, children: approved ? "✓ Freigegeben" : "🔍 Zur Implementierung freigeben" }), !approved && (_jsx("button", { className: "primary", onClick: handleCheck, disabled: running, style: { fontSize: 12, padding: "5px 14px" }, children: running ? "⏳ Prüfe…" : "Gate-Prüfung starten" }))] }), !checks && !running && !error && (_jsxs("p", { style: { fontSize: 13, color: "var(--muted)" }, children: ["Pr\u00FCft Validation, Contracts, Tests und KI-Analyse \u2014 setzt den Status auf ", _jsx("code", { children: "approved" }), " wenn alle Gates bestanden sind."] })), error && _jsx("p", { style: { color: "var(--red)", fontSize: 13 }, children: error }), checks && (_jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 8 }, children: [checks.map(c => (_jsxs("div", { style: {
                            display: "flex", gap: 10, alignItems: "flex-start",
                            padding: "8px 12px", borderRadius: 6,
                            background: c.passed
                                ? "color-mix(in srgb, var(--green) 10%, transparent)"
                                : "color-mix(in srgb, var(--red) 10%, transparent)",
                            border: `1px solid ${c.passed ? "var(--green)" : "var(--red)"}`,
                        }, children: [_jsx("span", { style: { fontSize: 16, flexShrink: 0 }, children: c.passed ? "✅" : "❌" }), _jsxs("div", { children: [_jsx("strong", { style: { fontSize: 13 }, children: c.name }), _jsx("p", { style: { fontSize: 12, color: "var(--muted)", marginTop: 2 }, children: c.message })] })] }, c.name))), allPassed && (_jsxs("p", { style: { color: "var(--green)", fontSize: 13, marginTop: 4 }, children: ["\u2713 Alle Gates bestanden \u2014 Spec ist jetzt ", _jsx("code", { children: "approved" }), ". Der Execute-Button erscheint oben."] })), !allPassed && (_jsx("p", { style: { color: "var(--muted)", fontSize: 12, marginTop: 4 }, children: "Behebe die fehlgeschlagenen Punkte und starte die Pr\u00FCfung erneut." }))] }))] }));
}
