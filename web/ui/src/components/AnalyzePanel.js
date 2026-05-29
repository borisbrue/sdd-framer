import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
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
function QuestionItem({ q, dismissed, docId, docContent, onToggleDismiss, onEdit, canEdit, }) {
    const [fetchingHint, setFetchingHint] = useState(false);
    const [hintError, setHintError] = useState("");
    const notify = useNotify();
    async function handleRequestHint() {
        setFetchingHint(true);
        setHintError("");
        try {
            const { suggested_fix } = await api.fetchFixHint(docId, q.text, q.section, docContent);
            notify("✓ KI-Vorschlag erhalten", "success");
            onEdit(suggested_fix);
        }
        catch (e) {
            const msg = e instanceof Error ? e.message : "Fehler beim Abrufen des Vorschlags.";
            setHintError(msg);
        }
        finally {
            setFetchingHint(false);
        }
    }
    return (_jsx("div", { style: {
            borderLeft: `3px solid ${SEVERITY_COLOR[q.severity]}`,
            paddingLeft: 10,
            marginBottom: 10,
            opacity: dismissed ? 0.45 : 1,
        }, children: _jsxs("div", { style: { display: "flex", gap: 6, alignItems: "flex-start" }, children: [_jsx("span", { style: { flexShrink: 0, fontSize: 13 }, children: SEVERITY_ICON[q.severity] }), _jsxs("div", { style: { flex: 1 }, children: [q.section && (_jsx("span", { style: { fontSize: 10, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, display: "block", marginBottom: 2 }, children: q.section })), _jsx("p", { style: { fontSize: 13, lineHeight: 1.5, marginBottom: 6 }, children: q.text }), _jsxs("div", { style: { display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }, children: [_jsx("button", { onClick: () => onToggleDismiss(q.id, !dismissed), style: { fontSize: 11, padding: "2px 8px", color: dismissed ? "var(--green)" : "var(--muted)", borderColor: dismissed ? "var(--green)" : "var(--border)" }, children: dismissed ? "↩ Wiederherstellen" : "✓ Abhaken" }), canEdit && !dismissed && (_jsxs(_Fragment, { children: [_jsx("button", { onClick: () => onEdit(null), style: { fontSize: 11, padding: "2px 8px", color: "var(--accent)", borderColor: "var(--accent)" }, children: "\u270F Bearbeiten" }), _jsx("button", { onClick: handleRequestHint, disabled: fetchingHint, style: { fontSize: 11, padding: "2px 8px", color: "var(--yellow)", borderColor: "var(--yellow)" }, children: fetchingHint ? "⏳ Lädt…" : "🤖 KI-Vorschlag" })] }))] }), hintError && (_jsx("p", { style: { fontSize: 11, color: "var(--red)", marginTop: 4 }, children: hintError }))] })] }) }));
}
function IssueItem({ issue, onEdit, }) {
    return (_jsx("div", { style: { borderLeft: `3px solid ${SEVERITY_COLOR[issue.severity]}`, paddingLeft: 10, marginBottom: 8 }, children: _jsxs("div", { style: { display: "flex", gap: 6 }, children: [_jsx("span", { style: { flexShrink: 0 }, children: SEVERITY_ICON[issue.severity] }), _jsxs("div", { style: { flex: 1 }, children: [issue.section && (_jsx("span", { style: { fontSize: 10, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, display: "block", marginBottom: 2 }, children: issue.section })), _jsx("p", { style: { fontSize: 13, lineHeight: 1.5, marginBottom: 4 }, children: issue.text }), _jsx("button", { onClick: () => onEdit(issue.suggested_fix ?? null), style: { fontSize: 11, padding: "2px 8px", color: "var(--accent)", borderColor: "var(--accent)" }, children: "\u270F \u00C4nderung bearbeiten" })] })] }) }));
}
function SuggestionItem({ s, onEdit, }) {
    return (_jsxs("div", { style: { borderLeft: "3px solid var(--accent)", paddingLeft: 10, marginBottom: 8 }, children: [_jsxs("p", { style: { fontSize: 13, lineHeight: 1.5, marginBottom: 4 }, children: ["\uD83D\uDCA1 ", s.text] }), _jsx("button", { onClick: () => onEdit(s.suggested_fix ?? null), style: { fontSize: 11, padding: "2px 8px", color: "var(--accent)", borderColor: "var(--accent)" }, children: "\u270F \u00C4nderung bearbeiten" })] }));
}
// ─── Body Editor ──────────────────────────────────────────────────────────────
function BodyEditor({ docId, initialBody, fixHint, onSaved, onClose, }) {
    const notify = useNotify();
    const [bodyText, setBodyText] = useState(initialBody);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    async function handleSave() {
        setSaving(true);
        setError("");
        try {
            await api.patchContractBody(docId, bodyText);
            notify("✓ Contract gespeichert", "success");
            onSaved();
            onClose();
        }
        catch (e) {
            setError(e instanceof Error ? e.message : "Fehler beim Speichern.");
        }
        finally {
            setSaving(false);
        }
    }
    function applyHint() {
        if (!fixHint)
            return;
        setBodyText(prev => prev + (prev.endsWith("\n") ? "" : "\n") + "\n" + fixHint);
    }
    return (_jsxs("div", { style: { marginTop: 16, borderTop: "1px solid var(--border)", paddingTop: 14 }, children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }, children: [_jsx("span", { style: { fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8 }, children: "Contract bearbeiten" }), _jsx("button", { onClick: onClose, style: { fontSize: 12, padding: "2px 8px" }, children: "\u00D7 Schlie\u00DFen" })] }), fixHint && (_jsxs("div", { style: { marginBottom: 10, background: "var(--surface)", border: "1px solid var(--accent)", borderRadius: 6, padding: 10 }, children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }, children: [_jsx("span", { style: { fontSize: 11, color: "var(--accent)", textTransform: "uppercase", letterSpacing: 0.8 }, children: "KI-Vorschlag" }), _jsx("button", { onClick: applyHint, style: { fontSize: 11, padding: "2px 8px", color: "var(--accent)", borderColor: "var(--accent)" }, children: "\u2193 Ans Ende anf\u00FCgen" })] }), _jsx("pre", { style: { fontSize: 12, whiteSpace: "pre-wrap", wordBreak: "break-word", margin: 0, color: "var(--fg)" }, children: fixHint })] })), _jsx("textarea", { value: bodyText, onChange: e => setBodyText(e.target.value), rows: 16, style: {
                    width: "100%", fontFamily: "monospace", fontSize: 12,
                    background: "var(--bg)", color: "var(--fg)", border: "1px solid var(--border)",
                    borderRadius: 6, padding: 10, resize: "vertical", boxSizing: "border-box",
                } }), error && _jsx("p", { style: { color: "var(--red)", fontSize: 13, marginTop: 6 }, children: error }), _jsxs("div", { style: { display: "flex", gap: 8, marginTop: 8 }, children: [_jsx("button", { className: "primary", onClick: handleSave, disabled: saving, style: { fontSize: 12, padding: "5px 14px" }, children: saving ? "Speichert…" : "💾 In Contract schreiben" }), _jsx("button", { onClick: onClose, style: { fontSize: 12, padding: "5px 14px" }, children: "Abbrechen" })] })] }));
}
// ─── Main Component ───────────────────────────────────────────────────────────
export default function AnalyzePanel({ docId, docContent, docType, autoTrigger = false, onBodySaved, forceStartKey }) {
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
    // Body-Editor
    const [editFixHint, setEditFixHint] = useState(null);
    const [editorOpen, setEditorOpen] = useState(false);
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
    // Force-open + auto-start when triggered externally (z.B. nach Restrukturierung)
    const [pendingAutoStart, setPendingAutoStart] = useState(false);
    const prevForceKeyRef = useRef(0);
    useEffect(() => {
        if (!forceStartKey || forceStartKey === prevForceKeyRef.current)
            return;
        prevForceKeyRef.current = forceStartKey;
        setOpen(true);
        setPendingAutoStart(true);
    }, [forceStartKey]);
    useEffect(() => {
        if (!pendingAutoStart || !open || starting || polling)
            return;
        setPendingAutoStart(false);
        startAnalysis();
    }, [pendingAutoStart, open, starting, polling]);
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
            setSummaries(prev => prev.map(s => s.result_id === current.result_id
                ? { ...s, dismissed_count: res.dismissed_ids.length }
                : s));
        }
        catch {
            setError("Fehler beim Speichern.");
        }
    }
    function handleEdit(hint) {
        setEditFixHint(hint);
        setEditorOpen(true);
    }
    function handleBodySaved() {
        setEditorOpen(false);
        setEditFixHint(null);
        onBodySaved?.();
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
    const canEdit = docType === "contract";
    return (_jsxs("section", { className: "card", style: { borderColor: "var(--yellow)" }, children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }, children: [_jsx("h3", { style: { fontSize: 12, color: "var(--yellow)", textTransform: "uppercase", letterSpacing: 1 }, children: "\uD83D\uDD0D KI-Analyse" }), _jsx("button", { onClick: () => { setOpen(false); stopPoll(); }, style: { fontSize: 12, padding: "2px 8px" }, children: "\u00D7" })] }), _jsxs("div", { style: { display: "flex", gap: 8, marginBottom: 14, alignItems: "center", flexWrap: "wrap" }, children: [_jsx("button", { className: "primary", onClick: startAnalysis, disabled: isRunning, style: { fontSize: 12, padding: "5px 14px", background: "var(--yellow)", borderColor: "var(--yellow)", color: "var(--bg)" }, children: starting ? "Startet…" : polling ? "⏳ Analysiert…" : current ? "Erneut analysieren" : "Analysieren" }), summaries.length > 0 && (_jsx("select", { value: selectedId ?? "", onChange: e => loadAnalysis(e.target.value), style: { fontSize: 11, padding: "3px 6px", background: "var(--surface)", color: "var(--fg)", border: "1px solid var(--border)", borderRadius: 4 }, children: summaries.map(s => (_jsxs("option", { value: s.result_id, children: [s.timestamp.replace("T", " ").slice(0, 16), " — ", s.question_count, "F ", s.issue_count, "P", s.dismissed_count > 0 ? ` (${s.dismissed_count}✓)` : ""] }, s.result_id))) })), current && !isRunning && (_jsx("span", { style: { fontSize: 11, color: "var(--muted)" }, children: activeQuestions.length > 0
                            ? `${activeQuestions.length} offen`
                            : "✓ Alle abgehakt" }))] }), error && _jsx("p", { style: { color: "var(--red)", fontSize: 13, marginBottom: 10 }, children: error }), polling && !current && (_jsx("p", { style: { color: "var(--muted)", fontSize: 13 }, children: "Claude analysiert das Dokument\u2026" })), loadingAnalysis && (_jsx("p", { style: { color: "var(--muted)", fontSize: 13 }, children: "Lade Analyse\u2026" })), !loadingAnalysis && current && (_jsxs("div", { children: [isEmpty && !isRunning && (_jsx("p", { style: { color: "var(--green)", fontSize: 13 }, children: "\u2713 Dokument sieht vollst\u00E4ndig aus." })), activeQuestions.length > 0 && (_jsxs("div", { style: { marginBottom: 14 }, children: [_jsx("p", { style: { fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }, children: "Nachfragen" }), activeQuestions.map(q => (_jsx(QuestionItem, { q: q, dismissed: false, docId: docId, docContent: docContent, onToggleDismiss: handleToggleDismiss, onEdit: handleEdit, canEdit: canEdit }, q.id)))] })), (current.issues?.length ?? 0) > 0 && (_jsxs("div", { style: { marginBottom: 14 }, children: [_jsx("p", { style: { fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }, children: "Probleme" }), current.issues.map((issue, i) => canEdit
                                ? _jsx(IssueItem, { issue: issue, onEdit: handleEdit }, i)
                                : (_jsx("div", { style: { borderLeft: `3px solid ${SEVERITY_COLOR[issue.severity]}`, paddingLeft: 10, marginBottom: 8 }, children: _jsxs("div", { style: { display: "flex", gap: 6 }, children: [_jsx("span", { style: { flexShrink: 0 }, children: SEVERITY_ICON[issue.severity] }), _jsxs("div", { children: [issue.section && (_jsx("span", { style: { fontSize: 10, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, display: "block", marginBottom: 2 }, children: issue.section })), _jsx("p", { style: { fontSize: 13, lineHeight: 1.5 }, children: issue.text })] })] }) }, i)))] })), (current.suggestions?.length ?? 0) > 0 && (_jsxs("div", { style: { marginBottom: 14 }, children: [_jsx("p", { style: { fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }, children: "Vorschl\u00E4ge" }), current.suggestions.map((s, i) => canEdit
                                ? _jsx(SuggestionItem, { s: s, onEdit: handleEdit }, i)
                                : (_jsx("div", { style: { borderLeft: "3px solid var(--accent)", paddingLeft: 10, marginBottom: 8 }, children: _jsxs("span", { style: { fontSize: 13 }, children: ["\uD83D\uDCA1 ", s.text] }) }, i)))] })), dismissedQuestions.length > 0 && (_jsxs("div", { style: { marginTop: 12, paddingTop: 10, borderTop: "1px solid var(--border)" }, children: [_jsxs("button", { onClick: () => setShowDismissed(v => !v), style: { fontSize: 11, color: "var(--muted)", background: "none", border: "none", cursor: "pointer", padding: 0 }, children: [showDismissed ? "▾" : "▸", " ", dismissedQuestions.length, " erledigte Punkte"] }), showDismissed && (_jsx("div", { style: { marginTop: 8 }, children: dismissedQuestions.map(q => (_jsx(QuestionItem, { q: q, dismissed: true, docId: docId, docContent: docContent, onToggleDismiss: handleToggleDismiss, onEdit: handleEdit, canEdit: canEdit }, q.id))) }))] })), canEdit && editorOpen && (_jsx(BodyEditor, { docId: docId, initialBody: docContent, fixHint: editFixHint, onSaved: handleBodySaved, onClose: () => { setEditorOpen(false); setEditFixHint(null); } }))] })), !loadingAnalysis && !current && !polling && !starting && summaries.length === 0 && (_jsx("p", { style: { color: "var(--muted)", fontSize: 13 }, children: "Noch keine Analysen. Klicke \u201EAnalysieren\" um zu starten." }))] }));
}
