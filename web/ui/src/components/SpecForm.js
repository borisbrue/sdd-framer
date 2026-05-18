import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { api } from "../api";
export default function SpecForm({ onCreated, onCancel }) {
    const [title, setTitle] = useState("");
    const [owner, setOwner] = useState("");
    const [priority, setPriority] = useState("medium");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    async function handleSubmit(e) {
        e.preventDefault();
        if (!title.trim())
            return;
        setLoading(true);
        setError("");
        try {
            const res = await api.createSpec({ title, owner, priority });
            onCreated(res.id);
        }
        catch (err) {
            setError(err instanceof Error ? err.message : "Fehler beim Anlegen.");
        }
        finally {
            setLoading(false);
        }
    }
    return (_jsxs("form", { onSubmit: handleSubmit, className: "card", style: { display: "flex", flexDirection: "column", gap: 12, marginBottom: 12 }, children: [_jsx("h3", { style: { fontSize: 14, fontWeight: 700 }, children: "Neue Spec" }), _jsxs("div", { children: [_jsx("label", { children: "Titel *" }), _jsx("input", { value: title, onChange: e => setTitle(e.target.value), placeholder: "z.B. User Registrierung", autoFocus: true, required: true })] }), _jsxs("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }, children: [_jsxs("div", { children: [_jsx("label", { children: "Owner" }), _jsx("input", { value: owner, onChange: e => setOwner(e.target.value), placeholder: "Name oder Team" })] }), _jsxs("div", { children: [_jsx("label", { children: "Priorit\u00E4t" }), _jsxs("select", { value: priority, onChange: e => setPriority(e.target.value), children: [_jsx("option", { value: "low", children: "low" }), _jsx("option", { value: "medium", children: "medium" }), _jsx("option", { value: "high", children: "high" }), _jsx("option", { value: "critical", children: "critical" })] })] })] }), error && _jsx("p", { style: { color: "var(--red)", fontSize: 13 }, children: error }), _jsxs("div", { style: { display: "flex", gap: 8, justifyContent: "flex-end" }, children: [_jsx("button", { type: "button", onClick: onCancel, children: "Abbrechen" }), _jsx("button", { type: "submit", className: "primary", disabled: loading || !title.trim(), children: loading ? "Anlegen…" : "Spec anlegen" })] })] }));
}
