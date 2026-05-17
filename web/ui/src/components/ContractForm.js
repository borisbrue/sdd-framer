import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { api } from "../api";
export default function ContractForm({ specId, onCreated, onCancel }) {
    const [formats, setFormats] = useState([]);
    const [format, setFormat] = useState("openapi");
    const [title, setTitle] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    useEffect(() => {
        api.getFormats().then((f) => { setFormats(f); setFormat(f[0] ?? "openapi"); });
    }, []);
    async function handleSubmit(e) {
        e.preventDefault();
        setLoading(true);
        setError("");
        try {
            await api.createContract({ spec_id: specId, format, title });
            onCreated();
        }
        catch (err) {
            setError(err instanceof Error ? err.message : "Fehler.");
        }
        finally {
            setLoading(false);
        }
    }
    return (_jsxs("form", { onSubmit: handleSubmit, className: "card", style: { display: "flex", flexDirection: "column", gap: 12, marginBottom: 12 }, children: [_jsxs("h3", { style: { fontSize: 14, fontWeight: 700 }, children: ["Neuer Contract f\u00FCr ", specId] }), _jsxs("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }, children: [_jsxs("div", { children: [_jsx("label", { children: "Format *" }), _jsx("select", { value: format, onChange: (e) => setFormat(e.target.value), children: formats.map((f) => _jsx("option", { children: f }, f)) })] }), _jsxs("div", { children: [_jsx("label", { children: "Titel (optional)" }), _jsx("input", { value: title, onChange: (e) => setTitle(e.target.value), placeholder: "z.B. login-api" })] })] }), error && _jsx("p", { style: { color: "var(--red)", fontSize: 13 }, children: error }), _jsxs("div", { style: { display: "flex", gap: 8, justifyContent: "flex-end" }, children: [_jsx("button", { type: "button", onClick: onCancel, children: "Abbrechen" }), _jsx("button", { type: "submit", className: "primary", disabled: loading, children: loading ? "Anlegen…" : "Contract anlegen" })] })] }));
}
