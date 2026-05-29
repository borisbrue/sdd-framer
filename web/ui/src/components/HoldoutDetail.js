import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { api } from "../api";
import IdChip from "./IdChip";
import MarkdownBody from "./MarkdownBody";
import OpenButton from "./OpenButton";
export default function HoldoutDetail({ holdoutId, onNavigate }) {
    const [holdout, setHoldout] = useState(null);
    const [loadError, setLoadError] = useState(null);
    const [editBody, setEditBody] = useState(null);
    const [saving, setSaving] = useState(false);
    const [msg, setMsg] = useState("");
    useEffect(() => {
        setHoldout(null);
        setLoadError(null);
        setEditBody(null);
        setMsg("");
        api.getHoldout(holdoutId)
            .then(setHoldout)
            .catch(e => setLoadError(e instanceof Error ? e.message : String(e)));
    }, [holdoutId]);
    if (loadError)
        return (_jsxs("div", { style: { padding: 20, color: "var(--red)", fontSize: 13 }, children: ["Fehler beim Laden: ", loadError] }));
    if (!holdout)
        return _jsx("div", { style: { padding: 20, color: "var(--muted)" }, children: "Lade\u2026" });
    const body = editBody ?? holdout.body;
    const dirty = editBody !== null && editBody !== holdout.body;
    const save = async () => {
        if (!dirty)
            return;
        setSaving(true);
        try {
            const res = await api.saveHoldout(holdout.spec, holdout.id, body);
            if (res.ok) {
                setHoldout(h => h ? { ...h, body } : h);
                setEditBody(null);
                setMsg("✓ Gespeichert");
            }
        }
        catch {
            setMsg("✗ Fehler");
        }
        finally {
            setSaving(false);
        }
    };
    return (_jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 20 }, children: [_jsx("div", { className: "card", children: _jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }, children: [_jsxs("div", { style: { flex: 1 }, children: [_jsxs("div", { style: { display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }, children: [_jsx(IdChip, { id: holdout.id, onClick: () => { } }), _jsxs("select", { value: holdout.status, onChange: async (e) => {
                                                const s = e.target.value;
                                                await api.patchHoldoutStatus(holdout.spec, holdout.id, s);
                                                setHoldout(h => h ? { ...h, status: s } : h);
                                            }, style: {
                                                fontSize: 11, background: "var(--surface)", color: "var(--muted)",
                                                border: "1px solid var(--border)", borderRadius: 4, padding: "2px 6px", cursor: "pointer",
                                            }, children: [_jsx("option", { value: "draft", children: "draft" }), _jsx("option", { value: "ready", children: "ready" }), _jsx("option", { value: "archived", children: "archived" })] })] }), _jsx("h2", { style: { fontSize: 20, fontWeight: 700, marginBottom: 8 }, children: holdout.title }), holdout.spec && (_jsxs("div", { style: { fontSize: 12, color: "var(--muted)" }, children: ["Spec: ", _jsx(IdChip, { id: holdout.spec, onClick: onNavigate })] }))] }), _jsx("div", { style: { display: "flex", gap: 8, flexShrink: 0 }, children: _jsx(OpenButton, { absFile: holdout.abs_file }) })] }) }), _jsxs("section", { className: "card", children: [_jsx("h3", { style: sectionHead, children: "Inhalt" }), _jsx("textarea", { value: body, onChange: e => { setEditBody(e.target.value); setMsg(""); }, style: {
                            width: "100%", minHeight: 300,
                            background: "var(--bg)", color: "var(--text)",
                            border: "1px solid var(--border)", borderRadius: 4,
                            fontFamily: "monospace", fontSize: 12, lineHeight: 1.6,
                            padding: 8, resize: "vertical", boxSizing: "border-box",
                            marginTop: 8,
                        } }), _jsxs("div", { style: { display: "flex", alignItems: "center", gap: 8, marginTop: 8 }, children: [_jsx("button", { onClick: save, disabled: !dirty || saving, style: {
                                    background: dirty ? "var(--accent)" : "var(--border)",
                                    color: dirty ? "var(--bg)" : "var(--muted)",
                                    border: "none", borderRadius: 4, padding: "3px 14px",
                                    fontSize: 12, fontWeight: 600,
                                    cursor: dirty && !saving ? "pointer" : "default",
                                }, children: saving ? "…" : "Speichern" }), dirty && (_jsx("button", { onClick: () => { setEditBody(null); setMsg(""); }, style: { background: "none", border: "none", color: "var(--muted)", fontSize: 11, cursor: "pointer" }, children: "Verwerfen" })), msg && (_jsx("span", { style: { fontSize: 11, color: msg.startsWith("✓") ? "var(--green)" : "var(--red)" }, children: msg }))] })] }), body.trim() && !dirty && (_jsxs("section", { className: "card", children: [_jsx("h3", { style: { ...sectionHead, marginBottom: 12 }, children: "Vorschau" }), _jsx(MarkdownBody, { markdown: body, onIdClick: onNavigate })] }))] }));
}
const sectionHead = {
    fontSize: 12,
    color: "var(--muted)",
    textTransform: "uppercase",
    letterSpacing: 1,
};
