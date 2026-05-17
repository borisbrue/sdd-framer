import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
const STATUS_ICON = {
    passed: "✓",
    failed: "✗",
    error: "✗",
    missing: "–",
    skipped: "◌",
};
const STATUS_COLOR = {
    passed: "var(--green)",
    failed: "var(--red)",
    error: "var(--red)",
    missing: "var(--yellow)",
    skipped: "var(--muted)",
};
export default function TestRunPanel({ specId }) {
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(false);
    const [error, setError] = useState(null);
    const fetchResults = useCallback(() => {
        setLoading(true);
        api.getTestResults(specId)
            .then(r => { setReport(r); setError(null); })
            .catch(() => { setReport(null); setError(null); })
            .finally(() => setLoading(false));
    }, [specId]);
    useEffect(() => { fetchResults(); }, [fetchResults]);
    const handleRun = async () => {
        setRunning(true);
        setError(null);
        try {
            const r = await api.triggerTestRun(specId);
            setReport(r);
        }
        catch (e) {
            setError(e instanceof Error ? e.message : "Unbekannter Fehler");
        }
        finally {
            setRunning(false);
        }
    };
    const sectionHead = {
        fontSize: 12, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1,
    };
    return (_jsxs("section", { className: "card", children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }, children: [_jsx("h3", { style: sectionHead, children: "Test Results" }), _jsx("button", { onClick: handleRun, disabled: running, style: { fontSize: 12 }, children: running ? "⏳ Läuft…" : "▶ Run Tests" })] }), error && (_jsxs("p", { style: { color: "var(--red)", fontSize: 13, marginBottom: 10 }, children: ["\u2717 ", error] })), loading && !running && (_jsx("p", { style: { color: "var(--muted)", fontSize: 13 }, children: "Lade\u2026" })), !loading && !report && !error && (_jsxs("p", { style: { color: "var(--muted)", fontSize: 13 }, children: ["Noch kein Test-Run. Klicke ", _jsx("strong", { children: "\u25B6 Run Tests" }), " um zu starten."] })), report && (_jsxs(_Fragment, { children: [_jsxs("div", { style: { display: "flex", gap: 16, fontSize: 13, marginBottom: 12, flexWrap: "wrap" }, children: [_jsxs("span", { style: { color: "var(--green)" }, children: ["\u2713 ", report.passed, " passed"] }), _jsxs("span", { style: { color: report.failed > 0 ? "var(--red)" : "var(--muted)" }, children: ["\u2717 ", report.failed, " failed"] }), _jsxs("span", { style: { color: "var(--muted)" }, children: ["\u25CC ", report.skipped, " skipped"] }), _jsxs("span", { style: { color: "var(--muted)", marginLeft: "auto" }, children: [report.duration_s.toFixed(2), "s \u00B7 ", report.started_at.slice(0, 19).replace("T", " ")] })] }), _jsxs("table", { style: { width: "100%", borderCollapse: "collapse", fontSize: 12 }, children: [_jsx("thead", { children: _jsxs("tr", { style: { color: "var(--muted)", textAlign: "left" }, children: [_jsx("th", { style: th, children: "TST-ID" }), _jsx("th", { style: th, children: "Status" }), _jsx("th", { style: th, children: "Artefakt" }), _jsx("th", { style: { ...th, textAlign: "right" }, children: "Dauer" })] }) }), _jsx("tbody", { children: report.tests.map(t => (_jsxs("tr", { style: { borderTop: "1px solid var(--border)" }, children: [_jsx("td", { style: { ...td, fontFamily: "monospace", color: "var(--accent)" }, children: t.test_id }), _jsxs("td", { style: { ...td, color: STATUS_COLOR[t.status] ?? "var(--text)" }, children: [STATUS_ICON[t.status], " ", t.status] }), _jsx("td", { style: { ...td, color: "var(--muted)", maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }, children: t.artifact || "—" }), _jsx("td", { style: { ...td, textAlign: "right", color: "var(--muted)" }, children: t.duration_s > 0 ? `${t.duration_s.toFixed(2)}s` : "—" })] }, t.test_id))) })] }), report.tests.filter(t => t.message).map(t => (_jsxs("details", { style: { marginTop: 8 }, children: [_jsxs("summary", { style: { fontSize: 12, color: STATUS_COLOR[t.status], cursor: "pointer" }, children: [t.test_id, " \u2013 Fehlermeldung"] }), _jsx("pre", { style: {
                                    marginTop: 6, padding: "8px 12px", background: "var(--surface)",
                                    borderRadius: 4, fontSize: 11, overflowX: "auto",
                                    color: "var(--red)", whiteSpace: "pre-wrap",
                                }, children: t.message })] }, t.test_id))), Object.keys(report.contract_coverage).length > 0 && (_jsxs("div", { style: { marginTop: 14, paddingTop: 10, borderTop: "1px solid var(--border)" }, children: [_jsx("div", { style: { fontSize: 11, color: "var(--muted)", marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }, children: "Contract-Coverage" }), _jsx("div", { style: { display: "flex", gap: 8, flexWrap: "wrap" }, children: Object.entries(report.contract_coverage).map(([con, covered]) => (_jsxs("span", { style: {
                                        fontSize: 11, padding: "2px 8px", borderRadius: 4,
                                        background: "var(--surface)",
                                        color: covered ? "var(--green)" : "var(--red)",
                                        border: `1px solid ${covered ? "var(--green)" : "var(--red)"}`,
                                    }, children: [covered ? "✓" : "✗", " ", con] }, con))) })] }))] }))] }));
}
const th = {
    padding: "4px 8px", fontWeight: 600, fontSize: 11,
};
const td = {
    padding: "5px 8px",
};
