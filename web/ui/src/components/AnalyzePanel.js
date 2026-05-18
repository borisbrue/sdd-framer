import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useNotify } from "./NotificationContext";
const AUTO_TRIGGER_DELAY_MS = 3000;
const POLL_INTERVAL_MS = 2000;
const SEVERITY_ICON = {
    error: "🔴",
    warning: "🟡",
    suggestion: "💡",
};
const SEVERITY_COLOR = {
    error: "var(--red)",
    warning: "var(--yellow)",
    suggestion: "var(--accent)",
};
// ─── Sub-components ───────────────────────────────────────────────────────────
function QuestionItem({ q, dismissed, onToggleDismiss, }) {
    return (_jsx("div", { style: {
            borderLeft: `3px solid ${SEVERITY_COLOR[q.severity]}`,
            paddingLeft: 10,
            marginBottom: 10,
            opacity: dismissed ? 0.45 : 1,
        }, children: _jsxs("div", { style: { display: "flex", gap: 6, alignItems: "flex-start" }, children: [_jsx("span", { style: { flexShrink: 0, fontSize: 13 }, children: SEVERITY_ICON[q.severity] }), _jsxs("div", { style: { flex: 1 }, children: [q.section && (_jsx("span", { style: { fontSize: 10, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, display: "block", marginBottom: 2 }, children: q.section })), _jsx("p", { style: { fontSize: 13, lineHeight: 1.5, marginBottom: 4 }, children: q.text }), _jsx("button", { onClick: () => onToggleDismiss(q.id, !dismissed), style: { fontSize: 11, padding: "2px 8px", color: dismissed ? "var(--green)" : "var(--muted)", borderColor: dismissed ? "var(--green)" : "var(--border)" }, children: dismissed ? "↩ Wiederherstellen" : "✓ Abhaken" })] })] }) }));
}
function IssueItem({ issue }) {
    return (_jsx("div", { style: { borderLeft: `3px solid ${SEVERITY_COLOR[issue.severity]}`, paddingLeft: 10, marginBottom: 8 }, children: _jsxs("div", { style: { display: "flex", gap: 6 }, children: [_jsx("span", { style: { flexShrink: 0 }, children: SEVERITY_ICON[issue.severity] }), _jsxs("div", { children: [issue.section && (_jsx("span", { style: { fontSize: 10, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, display: "block", marginBottom: 2 }, children: issue.section })), _jsx("p", { style: { fontSize: 13, lineHeight: 1.5 }, children: issue.text })] })] }) }));
}
// ─── Main Component ───────────────────────────────────────────────────────────
export default function AnalyzePanel({ docId, docContent, docType, autoTrigger = false }) {
    const notify = useNotify();
    const [open, setOpen] = useState(false);
    const [starting, setStarting] = useState(false);
    const [polling, setPolling] = useState(false);
    const [error, setError] = useState("");
    // Verlauf
    const [summaries, setSummaries] = useState([]);
    const [selectedId, setSelectedId] = useState(null);
    const [current, setCurrent] = useState(null);
    const [loadingAnalysis, setLoadingAnalysis] = useState(false);
    const [showDismissed, setShowDismissed] = useState(false);
    // Poll ref
    const pollRef = useRef(null);
    const prevContentRef = useRef(docContent);
    // Auto-trigger on content change
    useEffect(() => {
        if (!autoTrigger || !open || starting || polling)
            return;
        if (docContent === prevContentRef.current)
            return;
        prevContentRef.current = docContent;
        const timer = setTimeout(() => startAnalysis(), AUTO_TRIGGER_DELAY_MS);
        return () => clearTimeout(timer);
    }, [docContent, autoTrigger, open, starting, polling]);
    // Load summaries when panel opens
    useEffect(() => {
        if (!open)
            return;
        api.listAnalyses(docId).then(list => {
            setSummaries(list);
            if (list.length > 0 && selectedId === null) {
                loadAnalysis(list[0].result_id);
            }
        }).catch(() => { });
    }, [open, docId]);
    // Cleanup poll on unmount
    useEffect(() => () => stopPoll(), []);
    function stopPoll() {
        if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
        }
        setPolling(false);
    }
    async function loadAnalysis(resultId) {
        setLoadingAnalysis(true);
        setSelectedId(resultId);
        try {
            const a = await api.getAnalysis(docId, resultId);
            setCurrent(a);
        }
        catch {
            setError("Analyse konnte nicht geladen werden.");
        }
        finally {
            setLoadingAnalysis(false);
        }
    }
    async function startAnalysis() {
        setStarting(true);
        setError("");
        try {
            const dismissedIds = current?.dismissed_ids ?? [];
            const { job_id } = await api.analyzeStart(docId, {
                content: docContent,
                doc_type: docType,
                dismissed_ids: dismissedIds,
            });
            setPolling(true);
            pollRef.current = setInterval(async () => {
                try {
                    const status = await api.analyzeStatus(docId, job_id);
                    if (status.status === "complete" && status.result_id) {
                        stopPoll();
                        notify(`✓ Analyse für ${docId} abgeschlossen`, "success");
                        const [a, list] = await Promise.all([
                            api.getAnalysis(docId, status.result_id),
                            api.listAnalyses(docId),
                        ]);
                        setCurrent(a);
                        setSummaries(list);
                        setSelectedId(status.result_id);
                    }
                    else if (status.status === "failed") {
                        stopPoll();
                        setError(status.error ?? "Analyse fehlgeschlagen.");
                        notify(`✕ Analyse fehlgeschlagen: ${status.error ?? ""}`, "error");
                    }
                }
                catch {
                    stopPoll();
                    setError("Verbindung zum Server unterbrochen.");
                }
            }, POLL_INTERVAL_MS);
        }
        catch (e) {
            setError(e instanceof Error ? e.message : "Fehler beim Starten der Analyse.");
        }
        finally {
            setStarting(false);
        }
    }
    async function handleToggleDismiss(itemId, dismissed) {
        if (!current)
            return;
        try {
            const res = await api.dismissItem(docId, current.result_id, itemId, dismissed);
            setCurrent(prev => prev ? { ...prev, dismissed_ids: res.dismissed_ids } : prev);
            // refresh summary dismissed_count
            setSummaries(prev => prev.map(s => s.result_id === current.result_id
                ? { ...s, dismissed_count: res.dismissed_ids.length }
                : s));
        }
        catch {
            setError("Fehler beim Speichern.");
        }
    }
    // ─── Collapsed button ───────────────────────────────────────────────────────
    if (!open) {
        const pendingCount = current
            ? current.questions.filter(q => !current.dismissed_ids.includes(q.id)).length
            : 0;
        return (_jsxs("button", { onClick: () => setOpen(true), style: { fontSize: 12, padding: "4px 12px", color: "var(--yellow)", borderColor: "var(--yellow)" }, children: ["\uD83D\uDD0D KI-Analyse", pendingCount > 0 && (_jsx("span", { style: { marginLeft: 6, fontSize: 10, background: "var(--yellow)", color: "var(--bg)", borderRadius: 999, padding: "1px 5px" }, children: pendingCount }))] }));
    }
    // ─── Expanded panel ─────────────────────────────────────────────────────────
    const dismissedIds = current?.dismissed_ids ?? [];
    const activeQuestions = current?.questions.filter(q => !dismissedIds.includes(q.id)) ?? [];
    const dismissedQuestions = current?.questions.filter(q => dismissedIds.includes(q.id)) ?? [];
    const isEmpty = current && activeQuestions.length === 0 && (current.issues?.length ?? 0) === 0 && (current.suggestions?.length ?? 0) === 0;
    const isRunning = polling || starting;
    return (_jsxs("section", { className: "card", style: { borderColor: "var(--yellow)" }, children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }, children: [_jsx("h3", { style: { fontSize: 12, color: "var(--yellow)", textTransform: "uppercase", letterSpacing: 1 }, children: "\uD83D\uDD0D KI-Analyse" }), _jsx("button", { onClick: () => { setOpen(false); stopPoll(); }, style: { fontSize: 12, padding: "2px 8px" }, children: "\u00D7" })] }), _jsxs("div", { style: { display: "flex", gap: 8, marginBottom: 14, alignItems: "center", flexWrap: "wrap" }, children: [_jsx("button", { className: "primary", onClick: startAnalysis, disabled: isRunning, style: { fontSize: 12, padding: "5px 14px", background: "var(--yellow)", borderColor: "var(--yellow)", color: "var(--bg)" }, children: starting ? "Startet…" : polling ? "⏳ Analysiert…" : current ? "Erneut analysieren" : "Analysieren" }), summaries.length > 0 && (_jsx("select", { value: selectedId ?? "", onChange: e => loadAnalysis(e.target.value), style: { fontSize: 11, padding: "3px 6px", background: "var(--surface)", color: "var(--fg)", border: "1px solid var(--border)", borderRadius: 4 }, children: summaries.map(s => (_jsxs("option", { value: s.result_id, children: [s.timestamp.replace("T", " ").slice(0, 16), " — ", s.question_count, "F ", s.issue_count, "P", s.dismissed_count > 0 ? ` (${s.dismissed_count}✓)` : ""] }, s.result_id))) })), current && !isRunning && (_jsx("span", { style: { fontSize: 11, color: "var(--muted)" }, children: activeQuestions.length > 0
                            ? `${activeQuestions.length} offen`
                            : "✓ Alle abgehakt" }))] }), error && _jsx("p", { style: { color: "var(--red)", fontSize: 13, marginBottom: 10 }, children: error }), polling && !current && (_jsx("p", { style: { color: "var(--muted)", fontSize: 13 }, children: "Claude analysiert das Dokument\u2026" })), loadingAnalysis && (_jsx("p", { style: { color: "var(--muted)", fontSize: 13 }, children: "Lade Analyse\u2026" })), !loadingAnalysis && current && (_jsxs("div", { children: [isEmpty && !isRunning && (_jsx("p", { style: { color: "var(--green)", fontSize: 13 }, children: "\u2713 Dokument sieht vollst\u00E4ndig aus." })), activeQuestions.length > 0 && (_jsxs("div", { style: { marginBottom: 14 }, children: [_jsx("p", { style: { fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }, children: "Nachfragen" }), activeQuestions.map(q => (_jsx(QuestionItem, { q: q, dismissed: false, onToggleDismiss: handleToggleDismiss }, q.id)))] })), (current.issues?.length ?? 0) > 0 && (_jsxs("div", { style: { marginBottom: 14 }, children: [_jsx("p", { style: { fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }, children: "Probleme" }), current.issues.map((issue, i) => _jsx(IssueItem, { issue: issue }, i))] })), (current.suggestions?.length ?? 0) > 0 && (_jsxs("div", { style: { marginBottom: 14 }, children: [_jsx("p", { style: { fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }, children: "Vorschl\u00E4ge" }), current.suggestions.map((s, i) => (_jsx("div", { style: { borderLeft: "3px solid var(--accent)", paddingLeft: 10, marginBottom: 8 }, children: _jsxs("span", { style: { fontSize: 13 }, children: ["\uD83D\uDCA1 ", s.text] }) }, i)))] })), dismissedQuestions.length > 0 && (_jsxs("div", { style: { marginTop: 12, paddingTop: 10, borderTop: "1px solid var(--border)" }, children: [_jsxs("button", { onClick: () => setShowDismissed(v => !v), style: { fontSize: 11, color: "var(--muted)", background: "none", border: "none", cursor: "pointer", padding: 0 }, children: [showDismissed ? "▾" : "▸", " ", dismissedQuestions.length, " erledigte Punkte"] }), showDismissed && (_jsx("div", { style: { marginTop: 8 }, children: dismissedQuestions.map(q => (_jsx(QuestionItem, { q: q, dismissed: true, onToggleDismiss: handleToggleDismiss }, q.id))) }))] }))] })), !loadingAnalysis && !current && !polling && !starting && summaries.length === 0 && (_jsx("p", { style: { color: "var(--muted)", fontSize: 13 }, children: "Noch keine Analysen. Klicke \u201EAnalysieren\" um zu starten." }))] }));
}
