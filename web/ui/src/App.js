import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import AiUsageView from "./components/AiUsageView";
import ContractDetail from "./components/ContractDetail";
import HoldoutDetail from "./components/HoldoutDetail";
import ServerInfoPanel from "./components/ServerInfoPanel";
import SettingsPage from "./components/SettingsPage";
import SpecDetail from "./components/SpecDetail";
import SpecForm from "./components/SpecForm";
import SpecList from "./components/SpecList";
import StatusBar from "./components/StatusBar";
import TestDetail from "./components/TestDetail";
import { useTheme } from "./hooks/useTheme";
function idType(id) {
    const prefix = id.split("-")[0];
    if (prefix === "SPEC")
        return "spec";
    if (prefix === "CON")
        return "contract";
    if (prefix === "TST")
        return "test";
    if (prefix === "HOL")
        return "holdout";
    return "adr";
}
export default function App() {
    const { theme, setTheme } = useTheme();
    const [specs, setSpecs] = useState([]);
    const [contracts, setContracts] = useState([]);
    const [tests, setTests] = useState([]);
    const [selected, setSelected] = useState(null);
    const [history, setHistory] = useState([]);
    const [showSpecForm, setShowSpecForm] = useState(false);
    const [showAiUsage, setShowAiUsage] = useState(false);
    const [showSettings, setShowSettings] = useState(false);
    const [showServerInfo, setShowServerInfo] = useState(false);
    const [aiUsage, setAiUsage] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const mainRef = useRef(null);
    const refresh = useCallback(async () => {
        setLoading(true);
        setError("");
        try {
            const [s, c, t] = await Promise.all([
                api.getSpecs(), api.getContracts(), api.getTests(),
            ]);
            setSpecs(s);
            setContracts(c);
            setTests(t);
        }
        catch (e) {
            setError(e instanceof Error ? e.message : "Verbindungsfehler.");
        }
        finally {
            setLoading(false);
        }
    }, []);
    useEffect(() => { refresh(); }, [refresh]);
    function navigate(id) {
        const type = idType(id);
        if (type === "adr")
            return;
        const next = { type, id };
        setHistory(h => selected ? [...h, selected] : h);
        setSelected(next);
        setShowAiUsage(false);
        setShowSettings(false);
        mainRef.current?.scrollTo(0, 0);
    }
    function goBack() {
        const prev = history[history.length - 1] ?? null;
        setHistory(h => h.slice(0, -1));
        setSelected(prev);
    }
    function selectSpec(id) {
        setHistory([]);
        setSelected({ type: "spec", id });
        setShowAiUsage(false);
        setShowSettings(false);
        mainRef.current?.scrollTo(0, 0);
    }
    const selectedSpecId = selected?.type === "spec" ? selected.id : null;
    return (_jsxs("div", { style: { display: "flex", flexDirection: "column", height: "100vh" }, children: [_jsx(StatusBar, { onShowAiUsage: () => { api.aiUsage().then(setAiUsage); setShowAiUsage(v => !v); setShowSettings(false); setShowServerInfo(false); }, onShowSettings: () => { setShowSettings(v => !v); setShowAiUsage(false); setShowServerInfo(false); }, onShowServerInfo: () => setShowServerInfo(v => !v) }), showServerInfo && _jsx(ServerInfoPanel, { onClose: () => setShowServerInfo(false) }), _jsxs("div", { style: { display: "flex", flex: 1, overflow: "hidden" }, children: [_jsxs("aside", { style: {
                            width: 300, minWidth: 240,
                            borderRight: "1px solid var(--border)",
                            display: "flex", flexDirection: "column", overflow: "hidden",
                        }, children: [_jsxs("div", { style: { padding: "10px 10px 8px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }, children: [_jsxs("span", { style: { fontSize: 12, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1 }, children: ["Specs (", specs.length, ")"] }), _jsx("button", { onClick: () => setShowSpecForm(v => !v), style: { padding: "3px 8px", fontSize: 11 }, children: showSpecForm ? "×" : "+ Spec" })] }), _jsxs("div", { style: { overflowY: "auto", flex: 1, padding: 8 }, children: [showSpecForm && (_jsx(SpecForm, { onCreated: (id) => { setShowSpecForm(false); refresh().then(() => selectSpec(id)); }, onCancel: () => setShowSpecForm(false) })), loading && _jsx("p", { style: { color: "var(--muted)", padding: 8, fontSize: 13 }, children: "Laden\u2026" }), error && _jsx("p", { style: { color: "var(--red)", padding: 8, fontSize: 13 }, children: error }), !loading && !error && (_jsx(SpecList, { specs: specs, selected: selectedSpecId, onSelect: selectSpec }))] })] }), _jsxs("main", { ref: mainRef, style: { flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 0 }, children: [(selected || history.length > 0) && !showAiUsage && (_jsxs("div", { style: { display: "flex", alignItems: "center", gap: 8, marginBottom: 16, fontSize: 12, color: "var(--muted)" }, children: [history.length > 0 && (_jsx("button", { onClick: goBack, style: { padding: "3px 10px", fontSize: 12 }, children: "\u2190 Zur\u00FCck" })), history.map((h, i) => (_jsxs("span", { style: { display: "flex", alignItems: "center", gap: 6 }, children: [_jsx("span", { style: { color: "var(--accent)", cursor: "pointer", fontFamily: "monospace" }, onClick: () => {
                                                    setSelected(h);
                                                    setHistory(prev => prev.slice(0, i));
                                                }, children: h?.id }), _jsx("span", { children: "\u203A" })] }, i))), _jsx("span", { style: { fontFamily: "monospace", color: "var(--text)" }, children: selected?.id })] })), showAiUsage && aiUsage && (_jsx(AiUsageView, { usage: aiUsage, onClose: () => setShowAiUsage(false) })), showSettings && (_jsx(SettingsPage, { currentTheme: theme, onThemeChange: setTheme, onClose: () => setShowSettings(false) })), !showAiUsage && !showSettings && !selected && _jsx(EmptyState, { onNewSpec: () => setShowSpecForm(true) }), !showAiUsage && !showSettings && selected?.type === "spec" && (_jsx(SpecDetail, { specId: selected.id, contracts: contracts, tests: tests, onNavigate: navigate, onRefresh: refresh }, selected.id)), !showAiUsage && !showSettings && selected?.type === "contract" && (_jsx(ContractDetail, { contractId: selected.id, onNavigate: navigate }, selected.id)), !showAiUsage && !showSettings && selected?.type === "test" && (_jsx(TestDetail, { testId: selected.id, onNavigate: navigate }, selected.id)), !showAiUsage && !showSettings && selected?.type === "holdout" && (_jsx(HoldoutDetail, { holdoutId: selected.id, onNavigate: navigate }, selected.id))] })] })] }));
}
function EmptyState({ onNewSpec }) {
    return (_jsxs("div", { style: { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 16, color: "var(--muted)" }, children: [_jsx("div", { style: { fontSize: 48 }, children: "\uD83D\uDCCB" }), _jsx("p", { style: { fontSize: 16 }, children: "W\u00E4hle eine Spec aus der Liste" }), _jsx("p", { style: { fontSize: 13 }, children: "oder lege eine neue an." }), _jsx("button", { className: "primary", onClick: onNewSpec, children: "+ Neue Spec" })] }));
}
