import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { api } from "../api";
export default function ProjectForm({ onCreated, onCancel }) {
    const [name, setName] = useState("");
    const [owner, setOwner] = useState("");
    const [status, setStatus] = useState("active");
    const [description, setDescription] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    async function handleSubmit(e) {
        e.preventDefault();
        if (!name.trim())
            return;
        setLoading(true);
        setError("");
        try {
            const res = await api.createProject({ name, owner, status, description });
            onCreated(res.id);
        }
        catch (err) {
            setError(err instanceof Error ? err.message : "Fehler beim Anlegen.");
        }
        finally {
            setLoading(false);
        }
    }
    return (_jsxs("form", { onSubmit: handleSubmit, className: "card", style: { display: "flex", flexDirection: "column", gap: 12, marginBottom: 12 }, children: [_jsx("h3", { style: { fontSize: 14, fontWeight: 700 }, children: "Neues Projekt" }), _jsxs("div", { children: [_jsx("label", { children: "Name *" }), _jsx("input", { value: name, onChange: e => setName(e.target.value), placeholder: "z.B. Checkout-Backend", autoFocus: true, required: true })] }), _jsxs("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }, children: [_jsxs("div", { children: [_jsx("label", { children: "Owner" }), _jsx("input", { value: owner, onChange: e => setOwner(e.target.value), placeholder: "Name oder Team" })] }), _jsxs("div", { children: [_jsx("label", { children: "Status" }), _jsxs("select", { value: status, onChange: e => setStatus(e.target.value), children: [_jsx("option", { value: "planning", children: "planning" }), _jsx("option", { value: "active", children: "active" }), _jsx("option", { value: "archived", children: "archived" })] })] })] }), _jsxs("div", { children: [_jsx("label", { children: "Beschreibung" }), _jsx("textarea", { value: description, onChange: e => setDescription(e.target.value), placeholder: "Worum geht es in diesem Projekt?", style: { width: "100%", minHeight: 60, fontSize: 13, padding: 8, boxSizing: "border-box", background: "var(--bg)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: 4, resize: "vertical" } })] }), error && _jsx("p", { style: { color: "var(--red)", fontSize: 13 }, children: error }), _jsxs("div", { style: { display: "flex", gap: 8, justifyContent: "flex-end" }, children: [_jsx("button", { type: "button", onClick: onCancel, children: "Abbrechen" }), _jsx("button", { type: "submit", className: "primary", disabled: loading || !name.trim(), children: loading ? "Anlegen…" : "Projekt anlegen" })] })] }));
}
