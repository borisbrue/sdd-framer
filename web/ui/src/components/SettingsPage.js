import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { api } from "../api";
import { THEMES } from "../hooks/useTheme";
const ACCENT = {
    dark: "#89b4fa",
    light: "#2563eb",
    cyberpunk: "#00ffff",
};
const THEME_COLORS = {
    dark: { bg: "#1e1e2e", surface: "#2a2a3d", border: "#3d3d55", text: "#cdd6f4" },
    light: { bg: "#f4f4f8", surface: "#ffffff", border: "#d1d5db", text: "#1f2937" },
    cyberpunk: { bg: "#0a0a0f", surface: "#120820", border: "#ff00ff", text: "#e0d7ff" },
};
function ConfigEditor({ onSaved }) {
    const [tab, setTab] = useState("form");
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState(false);
    // Form state
    const [projectTitle, setProjectName] = useState("");
    const [evaluatorUrl, setEvaluatorUrl] = useState("");
    const [maxRetries, setMaxRetries] = useState(3);
    const [lifecycle, setLifecycle] = useState([]);
    const [newTag, setNewTag] = useState("");
    // Raw state
    const [rawYaml, setRawYaml] = useState("");
    useEffect(() => {
        setLoading(true);
        api.getConfig()
            .then(d => {
            setData(d);
            setProjectName(d.title);
            setEvaluatorUrl(d.evaluator_base_url);
            setMaxRetries(d.max_retries);
            setLifecycle(d.spec_lifecycle);
            setRawYaml(d.yaml);
        })
            .catch(() => setError("Config konnte nicht geladen werden."))
            .finally(() => setLoading(false));
    }, []);
    async function saveForm() {
        setSaving(true);
        setError("");
        setSuccess(false);
        try {
            await api.patchConfig({
                title: projectTitle,
                evaluator_base_url: evaluatorUrl,
                max_retries: maxRetries,
                spec_lifecycle: lifecycle,
            });
            setSuccess(true);
            onSaved();
            setTimeout(() => setSuccess(false), 2500);
        }
        catch (e) {
            setError(e instanceof Error ? e.message : "Speichern fehlgeschlagen.");
        }
        finally {
            setSaving(false);
        }
    }
    async function saveRaw() {
        setSaving(true);
        setError("");
        setSuccess(false);
        try {
            await api.saveConfigRaw(rawYaml);
            setSuccess(true);
            onSaved();
            setTimeout(() => setSuccess(false), 2500);
        }
        catch (e) {
            setError(e instanceof Error ? e.message : "Speichern fehlgeschlagen.");
        }
        finally {
            setSaving(false);
        }
    }
    function addTag() {
        const tag = newTag.trim();
        if (tag && !lifecycle.includes(tag)) {
            setLifecycle(prev => [...prev, tag]);
        }
        setNewTag("");
    }
    function removeTag(tag) {
        setLifecycle(prev => prev.filter(t => t !== tag));
    }
    if (loading)
        return _jsx("p", { style: { color: "var(--muted)", fontSize: 13 }, children: "Lade Config\u2026" });
    if (!data && error)
        return _jsx("p", { style: { color: "var(--red)", fontSize: 13 }, children: error });
    return (_jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 12 }, children: [_jsx("div", { style: { display: "flex", gap: 0, borderBottom: "1px solid var(--border)" }, children: ["form", "raw"].map(t => (_jsx("button", { onClick: () => setTab(t), style: {
                        padding: "6px 16px",
                        fontSize: 12,
                        borderRadius: 0,
                        border: "none",
                        borderBottom: tab === t ? "2px solid var(--accent)" : "2px solid transparent",
                        color: tab === t ? "var(--accent)" : "var(--muted)",
                        background: "none",
                        cursor: "pointer",
                    }, children: t === "form" ? "Felder" : "YAML (Erweitert)" }, t))) }), tab === "form" && (_jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 12 }, children: [_jsxs("div", { children: [_jsx("label", { style: labelStyle, children: "Projekttitel" }), _jsx("input", { value: projectTitle, onChange: e => setProjectName(e.target.value), placeholder: "My Project", style: { width: "100%" } })] }), _jsxs("div", { children: [_jsx("label", { style: labelStyle, children: "Evaluator-URL" }), _jsx("input", { value: evaluatorUrl, onChange: e => setEvaluatorUrl(e.target.value), placeholder: "http://localhost:8000", style: { width: "100%" } })] }), _jsxs("div", { children: [_jsx("label", { style: labelStyle, children: "Max. Retries (Orchestrator)" }), _jsx("input", { type: "number", min: 1, max: 10, value: maxRetries, onChange: e => setMaxRetries(Number(e.target.value)), style: { width: 80 } })] }), _jsxs("div", { children: [_jsx("label", { style: labelStyle, children: "Spec-Lifecycle" }), _jsxs("div", { style: { display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }, children: [lifecycle.map(tag => (_jsxs("span", { style: {
                                            display: "flex", alignItems: "center", gap: 4,
                                            background: "var(--surface)", border: "1px solid var(--border)",
                                            borderRadius: 4, padding: "2px 8px", fontSize: 12,
                                        }, children: [tag, _jsx("button", { onClick: () => removeTag(tag), style: {
                                                    border: "none", background: "none", padding: 0,
                                                    cursor: "pointer", color: "var(--muted)", fontSize: 12, lineHeight: 1,
                                                }, children: "\u00D7" })] }, tag))), _jsxs("div", { style: { display: "flex", gap: 4 }, children: [_jsx("input", { value: newTag, onChange: e => setNewTag(e.target.value), onKeyDown: e => { if (e.key === "Enter") {
                                                    e.preventDefault();
                                                    addTag();
                                                } }, placeholder: "+ Status", style: { width: 100, padding: "2px 8px", fontSize: 12 } }), _jsx("button", { onClick: addTag, style: { padding: "2px 8px", fontSize: 12 }, children: "+" })] })] }), _jsx("p", { style: { fontSize: 11, color: "var(--muted)", marginTop: 4 }, children: "Reihenfolge = Lifecycle-Flow. Enter oder + dr\u00FCcken zum Hinzuf\u00FCgen." })] }), _jsxs("div", { style: { display: "flex", gap: 8, alignItems: "center" }, children: [_jsx("button", { className: "primary", disabled: saving, onClick: saveForm, children: saving ? "Speichert…" : "Speichern" }), success && _jsx("span", { style: { fontSize: 12, color: "var(--green)" }, children: "\u2713 Gespeichert" }), error && _jsx("span", { style: { fontSize: 12, color: "var(--red)" }, children: error })] })] })), tab === "raw" && (_jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 10 }, children: [_jsxs("p", { style: { fontSize: 11, color: "var(--muted)" }, children: ["Direktes Bearbeiten der ", _jsx("code", { children: ".sdd/config.yaml" }), ". YAML muss syntaktisch korrekt sein."] }), _jsx("textarea", { value: rawYaml, onChange: e => setRawYaml(e.target.value), rows: 20, spellCheck: false, style: {
                            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                            fontSize: 12,
                            lineHeight: 1.6,
                            padding: "10px 12px",
                            resize: "vertical",
                            width: "100%",
                            background: "#1d2021",
                            color: "#ebdbb2",
                            border: "1px solid var(--border)",
                            borderRadius: "var(--radius)",
                        } }), _jsxs("div", { style: { display: "flex", gap: 8, alignItems: "center" }, children: [_jsx("button", { className: "primary", disabled: saving, onClick: saveRaw, children: saving ? "Speichert…" : "YAML speichern" }), success && _jsx("span", { style: { fontSize: 12, color: "var(--green)" }, children: "\u2713 Gespeichert" }), error && _jsx("span", { style: { fontSize: 12, color: "var(--red)" }, children: error })] })] }))] }));
}
export default function SettingsPage({ currentTheme, onThemeChange, onClose }) {
    return (_jsxs("div", { children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }, children: [_jsx("h2", { style: { fontSize: 20, fontWeight: 700 }, children: "Einstellungen" }), _jsx("button", { onClick: onClose, style: { padding: "4px 12px" }, children: "\u00D7 Schlie\u00DFen" })] }), _jsxs("section", { className: "card", style: { marginBottom: 16 }, children: [_jsx("h3", { style: sectionHead, children: "Erscheinungsbild" }), _jsx("div", { style: { display: "flex", gap: 16, flexWrap: "wrap" }, children: THEMES.map(({ id, label }) => {
                            const active = id === currentTheme;
                            const c = THEME_COLORS[id];
                            return (_jsxs("button", { onClick: () => onThemeChange(id), style: {
                                    padding: 0,
                                    border: `2px solid ${active ? ACCENT[id] : "var(--border)"}`,
                                    borderRadius: "var(--radius)",
                                    background: "none",
                                    cursor: "pointer",
                                    width: 160,
                                    overflow: "hidden",
                                    transition: "border-color 0.2s, transform 0.1s",
                                    transform: active ? "scale(1.03)" : "scale(1)",
                                }, children: [_jsxs("div", { style: { background: c.bg, padding: 12, display: "flex", flexDirection: "column", gap: 6 }, children: [_jsxs("div", { style: { background: c.surface, border: `1px solid ${c.border}`, borderRadius: 4, padding: "6px 10px" }, children: [_jsx("div", { style: { width: "60%", height: 6, background: ACCENT[id], borderRadius: 3, marginBottom: 4 } }), _jsx("div", { style: { width: "40%", height: 4, background: c.text, borderRadius: 2, opacity: 0.5 } })] }), _jsxs("div", { style: { display: "flex", gap: 4 }, children: [_jsx("div", { style: { flex: 1, height: 4, background: c.border, borderRadius: 2, opacity: 0.6 } }), _jsx("div", { style: { flex: 2, height: 4, background: c.text, borderRadius: 2, opacity: 0.3 } })] })] }), _jsxs("div", { style: {
                                            background: c.surface,
                                            borderTop: `1px solid ${c.border}`,
                                            padding: "8px 12px",
                                            display: "flex",
                                            justifyContent: "space-between",
                                            alignItems: "center",
                                        }, children: [_jsx("span", { style: { color: c.text, fontSize: 13, fontWeight: active ? 700 : 400 }, children: label }), active && (_jsx("span", { style: { color: ACCENT[id], fontSize: 11 }, children: "\u2713 aktiv" }))] })] }, id));
                        }) })] }), _jsxs("section", { className: "card", children: [_jsx("h3", { style: { ...sectionHead, marginBottom: 16 }, children: "Projekt-Config (.sdd/config.yaml)" }), _jsx(ConfigEditor, { onSaved: () => { } })] })] }));
}
const sectionHead = {
    fontSize: 12,
    color: "var(--muted)",
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 16,
};
const labelStyle = {
    display: "block",
    fontSize: 12,
    color: "var(--muted)",
    marginBottom: 4,
};
