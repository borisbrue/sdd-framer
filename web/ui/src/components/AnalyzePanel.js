import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState, useEffect, useRef } from "react";
import { api } from "../api";
const AUTO_TRIGGER_DELAY_MS = 3000;
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
function QuestionItem({ q, answered, onAnswer, }) {
    const [open, setOpen] = useState(false);
    const [text, setText] = useState(answered?.answer ?? "");
    const isAnswered = !!answered;
    return (_jsx("div", { style: {
            borderLeft: `3px solid ${SEVERITY_COLOR[q.severity]}`,
            paddingLeft: 10,
            marginBottom: 10,
            opacity: isAnswered ? 0.45 : 1,
        }, children: _jsxs("div", { style: { display: "flex", gap: 6, alignItems: "flex-start" }, children: [_jsx("span", { style: { flexShrink: 0, fontSize: 13 }, children: SEVERITY_ICON[q.severity] }), _jsxs("div", { style: { flex: 1 }, children: [q.section && (_jsx("span", { style: { fontSize: 10, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, display: "block", marginBottom: 2 }, children: q.section })), _jsx("p", { style: { fontSize: 13, lineHeight: 1.5, marginBottom: 4 }, children: q.text }), isAnswered
                            ? (_jsxs("span", { style: { fontSize: 11, color: "var(--green)" }, children: ["\u2713 Beantwortet", answered.answer ? `: ${answered.answer}` : ""] }))
                            : (_jsx("div", { children: open ? (_jsxs("div", { children: [_jsx("textarea", { value: text, onChange: e => setText(e.target.value), placeholder: "Deine Antwort (optional)\u2026", style: { fontSize: 12, minHeight: 50, marginBottom: 6 } }), _jsxs("div", { style: { display: "flex", gap: 6 }, children: [_jsx("button", { className: "primary", onClick: () => onAnswer(q.id, text), style: { fontSize: 11, padding: "3px 10px" }, children: "Als beantwortet markieren" }), _jsx("button", { onClick: () => setOpen(false), style: { fontSize: 11, padding: "3px 10px" }, children: "Abbrechen" })] })] })) : (_jsx("button", { onClick: () => setOpen(true), style: { fontSize: 11, padding: "2px 8px", color: "var(--muted)", borderColor: "var(--border)" }, children: "Beantworten" })) }))] })] }) }));
}
function IssueItem({ issue }) {
    return (_jsx("div", { style: {
            borderLeft: `3px solid ${SEVERITY_COLOR[issue.severity]}`,
            paddingLeft: 10,
            marginBottom: 8,
        }, children: _jsxs("div", { style: { display: "flex", gap: 6 }, children: [_jsx("span", { style: { flexShrink: 0 }, children: SEVERITY_ICON[issue.severity] }), _jsxs("div", { children: [issue.section && (_jsx("span", { style: { fontSize: 10, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, display: "block", marginBottom: 2 }, children: issue.section })), _jsx("p", { style: { fontSize: 13, lineHeight: 1.5 }, children: issue.text })] })] }) }));
}
export default function AnalyzePanel({ docId, docContent, docType, autoTrigger = false }) {
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const prevContentRef = useRef(docContent);
    useEffect(() => {
        if (!autoTrigger || !open || loading)
            return;
        if (docContent === prevContentRef.current)
            return;
        prevContentRef.current = docContent;
        const timer = setTimeout(() => runAnalysis(), AUTO_TRIGGER_DELAY_MS);
        return () => clearTimeout(timer);
    }, [docContent, autoTrigger, open, loading]);
    const [error, setError] = useState("");
    const [sessionId, setSessionId] = useState(null);
    const [answered, setAnswered] = useState([]);
    const [questions, setQuestions] = useState([]);
    const [issues, setIssues] = useState([]);
    const [suggestions, setSuggestions] = useState([]);
    const [hasResult, setHasResult] = useState(false);
    const openCount = questions.filter(q => !answered.find(a => a.id === q.id)).length;
    async function runAnalysis() {
        setLoading(true);
        setError("");
        try {
            const res = await api.analyzeDoc(docId, {
                content: docContent,
                doc_type: docType,
                session_id: sessionId,
                answered_questions: answered,
            });
            setSessionId(res.session_id);
            setQuestions(res.questions);
            setIssues(res.issues);
            setSuggestions(res.suggestions);
            setHasResult(true);
        }
        catch (e) {
            setError(e instanceof Error ? e.message : "Fehler bei der Analyse.");
        }
        finally {
            setLoading(false);
        }
    }
    function handleAnswer(id, answer) {
        setAnswered(prev => [...prev.filter(a => a.id !== id), { id, answer }]);
    }
    const allAnswered = hasResult && questions.length > 0 && questions.every(q => answered.find(a => a.id === q.id));
    const isEmpty = hasResult && questions.length === 0 && issues.length === 0 && suggestions.length === 0;
    if (!open) {
        return (_jsxs("button", { onClick: () => setOpen(true), style: { fontSize: 12, padding: "4px 12px", color: "var(--yellow)", borderColor: "var(--yellow)" }, children: ["\uD83D\uDD0D KI-Analyse", answered.length > 0 && (_jsxs("span", { style: { marginLeft: 6, fontSize: 10, background: "var(--yellow)", color: "var(--bg)", borderRadius: 999, padding: "1px 5px" }, children: [answered.length, " beantwortet"] }))] }));
    }
    return (_jsxs("section", { className: "card", style: { borderColor: "var(--yellow)" }, children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }, children: [_jsx("h3", { style: { fontSize: 12, color: "var(--yellow)", textTransform: "uppercase", letterSpacing: 1 }, children: "\uD83D\uDD0D KI-Analyse" }), _jsx("button", { onClick: () => setOpen(false), style: { fontSize: 12, padding: "2px 8px" }, children: "\u00D7" })] }), _jsxs("div", { style: { display: "flex", gap: 8, marginBottom: 14, alignItems: "center" }, children: [_jsx("button", { className: "primary", onClick: runAnalysis, disabled: loading, style: { fontSize: 12, padding: "5px 14px", background: "var(--yellow)", borderColor: "var(--yellow)", color: "var(--bg)" }, children: loading ? "Analysiere…" : hasResult ? "Erneut analysieren" : "Analysieren" }), hasResult && !loading && (_jsx("span", { style: { fontSize: 11, color: "var(--muted)" }, children: openCount > 0
                            ? `${openCount} offene Frage${openCount > 1 ? "n" : ""}`
                            : allAnswered ? "✓ Alle Fragen beantwortet" : "Keine Fragen" }))] }), error && (_jsx("p", { style: { color: "var(--red)", fontSize: 13, marginBottom: 10 }, children: error })), loading && (_jsx("p", { style: { color: "var(--muted)", fontSize: 13 }, children: "Claude analysiert das Dokument\u2026" })), !loading && hasResult && (_jsxs("div", { children: [isEmpty && (_jsx("p", { style: { color: "var(--green)", fontSize: 13 }, children: "\u2713 Dokument sieht vollst\u00E4ndig aus. Keine offenen Punkte." })), questions.length > 0 && (_jsxs("div", { style: { marginBottom: 14 }, children: [_jsx("p", { style: { fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }, children: "Nachfragen" }), questions.map(q => (_jsx(QuestionItem, { q: q, answered: answered.find(a => a.id === q.id), onAnswer: handleAnswer }, q.id)))] })), issues.length > 0 && (_jsxs("div", { style: { marginBottom: 14 }, children: [_jsx("p", { style: { fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }, children: "Probleme" }), issues.map((issue, i) => _jsx(IssueItem, { issue: issue }, i))] })), suggestions.length > 0 && (_jsxs("div", { children: [_jsx("p", { style: { fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }, children: "Vorschl\u00E4ge" }), suggestions.map((s, i) => (_jsx("div", { style: { borderLeft: "3px solid var(--accent)", paddingLeft: 10, marginBottom: 8 }, children: _jsxs("span", { style: { fontSize: 13 }, children: ["\uD83D\uDCA1 ", s.text] }) }, i)))] })), answered.length > 0 && (_jsx("div", { style: { marginTop: 12, paddingTop: 10, borderTop: "1px solid var(--border)" }, children: _jsxs("button", { onClick: runAnalysis, disabled: loading, style: { fontSize: 11, padding: "3px 10px", color: "var(--accent)", borderColor: "var(--accent)" }, children: ["Erneut analysieren mit ", answered.length, " Antworten"] }) }))] }))] }));
}
