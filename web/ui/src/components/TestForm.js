import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
import { useState } from "react";
import { api } from "../api";
const LEVELS = ["unit", "integration", "contract", "acceptance", "performance", "property"];
export default function TestForm({ specId, contracts, onCreated, onCancel }) {
    const [contractId, setContractId] = useState(contracts[0]?.id ?? "");
    const [level, setLevel] = useState("contract");
    const [title, setTitle] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    async function handleSubmit(e) {
        e.preventDefault();
        setLoading(true);
        setError("");
        try {
            await api.createTest({ spec_id: specId, contract_id: contractId, level, title });
            onCreated();
        }
        catch (err) {
            setError(err instanceof Error ? err.message : "Fehler.");
        }
        finally {
            setLoading(false);
        }
    }
    return (_jsxs("form", { onSubmit: handleSubmit, className: "card", style: { display: "flex", flexDirection: "column", gap: 12, marginBottom: 12 }, children: [_jsxs("h3", { style: { fontSize: 14, fontWeight: 700 }, children: ["Neuer Test f\u00FCr ", specId] }), _jsxs("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }, children: [_jsxs("div", { children: [_jsx("label", { children: "Contract *" }), _jsx("select", { value: contractId, onChange: (e) => setContractId(e.target.value), children: contracts.map((c) => (_jsxs("option", { value: c.id, children: [c.id, " ", c.title] }, c.id))) })] }), _jsxs("div", { children: [_jsx("label", { children: "Level *" }), _jsx("select", { value: level, onChange: (e) => setLevel(e.target.value), children: LEVELS.map((l) => _jsx("option", { children: l }, l)) })] }), _jsxs("div", { children: [_jsx("label", { children: "Titel (optional)" }), _jsx("input", { value: title, onChange: (e) => setTitle(e.target.value), placeholder: "z.B. login-happy-path" })] })] }), error && _jsx("p", { style: { color: "var(--red)", fontSize: 13 }, children: error }), _jsxs("div", { style: { display: "flex", gap: 8, justifyContent: "flex-end" }, children: [_jsx("button", { type: "button", onClick: onCancel, children: "Abbrechen" }), _jsx("button", { type: "submit", className: "primary", disabled: loading, children: loading ? "Anlegen…" : "Test anlegen" })] })] }));
}
