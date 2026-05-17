import { jsxs as _jsxs, jsx as _jsx, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useRef, useState } from "react";
import { api } from "../api";
const POLL_INTERVAL = 5000;
const SESSION_KEY = (specId) => `sdd-pipeline-${specId}`;
const TERMINAL = ["labeled", "merged", "failed", "dry_run", "aborted"];
export default function ExecutePanel({ spec, onStatusChange }) {
    const [run, setRun] = useState(null);
    const [logLines, setLogLines] = useState([]);
    const [showModal, setShowModal] = useState(false);
    const [baseUrl, setBaseUrl] = useState("");
    const [projectId, setProjectId] = useState(spec.project ?? "");
    const [dryRun, setDryRun] = useState(false);
    const [noPr, setNoPr] = useState(false);
    const [hasClaudeCli, setHasClaudeCli] = useState(true);
    const [projectRoot, setProjectRoot] = useState("");
    const [starting, setStarting] = useState(false);
    const pollRef = useRef(null);
    const esRef = useRef(null);
    const logRef = useRef(null);
    // Load status + prefill base_url on mount
    useEffect(() => {
        api.getStatus().then(s => {
            setHasClaudeCli(s.has_claude_cli ?? true);
            setBaseUrl(s.evaluator_base_url ?? "");
            setProjectRoot(s.project_root ?? "");
        }).catch(() => { });
    }, []);
    // Auto-scroll log to bottom on new lines
    useEffect(() => {
        if (logRef.current) {
            logRef.current.scrollTop = logRef.current.scrollHeight;
        }
    }, [logLines]);
    // Restore run from sessionStorage or active-run endpoint on mount
    useEffect(() => {
        if (spec.status !== "approved")
            return;
        const storedId = sessionStorage.getItem(SESSION_KEY(spec.id));
        if (storedId) {
            api.getPipelineRun(storedId)
                .then(r => {
                setRun(r);
                if (!TERMINAL.includes(r.status)) {
                    startPolling(storedId);
                    startStreaming(storedId);
                }
                else {
                    setLogLines(r.log ?? []);
                }
            })
                .catch(() => {
                sessionStorage.removeItem(SESSION_KEY(spec.id));
                tryActiveRun();
            });
        }
        else {
            tryActiveRun();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [spec.id]);
    function tryActiveRun() {
        api.getActivePipeline(spec.id)
            .then(r => { setRun(r); startPolling(r.run_id); startStreaming(r.run_id); })
            .catch(() => { });
    }
    function startStreaming(runId) {
        if (esRef.current) {
            esRef.current.close();
            esRef.current = null;
        }
        const es = api.streamPipelineLog(runId, (line) => setLogLines(prev => [...prev, line]), () => { esRef.current = null; });
        esRef.current = es;
    }
    function startPolling(runId) {
        if (pollRef.current)
            clearInterval(pollRef.current);
        pollRef.current = setInterval(async () => {
            try {
                const r = await api.getPipelineRun(runId);
                setRun(r);
                if (TERMINAL.includes(r.status)) {
                    clearInterval(pollRef.current);
                    pollRef.current = null;
                    sessionStorage.removeItem(SESSION_KEY(spec.id));
                    if (r.log?.length)
                        setLogLines(r.log);
                    if (r.status === "labeled" || r.status === "merged")
                        onStatusChange();
                }
            }
            catch {
                clearInterval(pollRef.current);
                pollRef.current = null;
            }
        }, POLL_INTERVAL);
    }
    useEffect(() => () => {
        if (pollRef.current)
            clearInterval(pollRef.current);
        if (esRef.current) {
            esRef.current.close();
            esRef.current = null;
        }
    }, []);
    async function handleExecute() {
        setStarting(true);
        try {
            const { run_id } = await api.orchestrate({
                spec_id: spec.id,
                project_id: projectId || undefined,
                dry_run: dryRun,
                no_pr: noPr,
                base_url: baseUrl || undefined,
            });
            sessionStorage.setItem(SESSION_KEY(spec.id), run_id);
            const initial = await api.getPipelineRun(run_id);
            setRun(initial);
            setLogLines([]);
            setShowModal(false);
            startStreaming(run_id);
            startPolling(run_id);
        }
        catch (e) {
            alert(`Execute fehlgeschlagen: ${e instanceof Error ? e.message : String(e)}`);
        }
        finally {
            setStarting(false);
        }
    }
    async function handleAbort() {
        if (!run)
            return;
        try {
            await api.abortPipeline(run.run_id);
        }
        catch {
            // Ignore — run may have finished between click and request
        }
    }
    if (spec.status !== "approved")
        return null;
    const isRunning = run?.status === "running";
    const isDone = run && TERMINAL.includes(run.status);
    return (_jsxs(_Fragment, { children: [run && (_jsx("div", { className: "card", style: { borderColor: panelBorder(run.status), marginBottom: 0 }, children: _jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start" }, children: [_jsxs("div", { style: { flex: 1, minWidth: 0 }, children: [_jsxs("div", { style: { fontWeight: 600, marginBottom: 6, display: "flex", alignItems: "center", gap: 10 }, children: [_jsxs("span", { children: [statusIcon(run.status), " ", statusTitle(run, spec.id)] }), run.status === "running" && (_jsx("button", { style: { fontSize: 11, padding: "2px 8px", color: "var(--red)", borderColor: "var(--red)" }, onClick: handleAbort, children: "\u2298 Abbrechen" }))] }), logLines.length > 0 && (_jsxs("div", { ref: logRef, style: {
                                        background: "#1d2021",
                                        color: "#ebdbb2",
                                        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                                        fontSize: 11,
                                        lineHeight: 1.55,
                                        padding: "8px 12px",
                                        borderRadius: 4,
                                        height: 220,
                                        overflowY: "auto",
                                        marginBottom: isDone ? 8 : 0,
                                        border: "1px solid #504945",
                                    }, children: [logLines.map((line, i) => (_jsx("div", { style: { color: lineColor(line), whiteSpace: "pre-wrap" }, children: line }, i))), !isDone && (_jsx("span", { style: { color: "var(--accent)", opacity: 0.7 }, children: "\u258C" }))] })), isDone && _jsx(AttemptSummary, { attempts: run.attempts, status: run.status, issueUrl: run.issue_url })] }), isDone && (_jsx("button", { style: { fontSize: 12, marginLeft: 8 }, onClick: () => { setRun(null); setLogLines([]); }, children: "\u2715" }))] }) })), !isDone && (_jsx("div", { style: { display: "flex", justifyContent: "flex-end" }, children: _jsx("button", { className: "primary", disabled: isRunning, onClick: () => setShowModal(true), style: { minWidth: 110 }, children: isRunning ? "⚙ läuft…" : "▶ Execute" }) })), showModal && (_jsx("div", { style: modalOverlay, onClick: () => setShowModal(false), children: _jsxs("div", { style: modalBox, onClick: e => e.stopPropagation(), children: [_jsx("h3", { style: { marginBottom: 12 }, children: "Pipeline starten" }), _jsxs("div", { style: { fontSize: 13, color: "var(--muted)", marginBottom: 16 }, children: [_jsx("code", { style: { color: "var(--accent)" }, children: spec.id }), " \u2014 ", spec.title] }), !hasClaudeCli && (_jsxs("div", { style: { background: "color-mix(in srgb, var(--red) 15%, transparent)", border: "1px solid var(--red)", borderRadius: "var(--radius)", padding: "8px 12px", marginBottom: 14, fontSize: 12, color: "var(--red)" }, children: ["\u26A0 Claude Code CLI nicht gefunden. Stelle sicher, dass ", _jsx("code", { children: "claude" }), " im PATH installiert und eingeloggt ist."] })), projectRoot && (_jsxs("div", { style: { fontSize: 11, color: "var(--muted)", marginBottom: 14 }, children: ["Code wird geschrieben nach: ", _jsx("code", { style: { color: "var(--text)" }, children: projectRoot })] })), _jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }, children: [_jsxs("div", { children: [_jsx("label", { children: "Base-URL f\u00FCr Evaluator (leer = kein Evaluator)" }), _jsx("input", { value: baseUrl, onChange: e => setBaseUrl(e.target.value), placeholder: "http://localhost:8000" })] }), _jsxs("div", { children: [_jsx("label", { children: "Project ID (optional)" }), _jsx("input", { value: projectId, onChange: e => setProjectId(e.target.value), placeholder: spec.project ?? "" })] }), _jsxs("label", { style: { display: "flex", gap: 8, alignItems: "center", cursor: "pointer", fontSize: 13, color: "var(--text)" }, children: [_jsx("input", { type: "checkbox", checked: dryRun, onChange: e => setDryRun(e.target.checked) }), "Dry-run (kein Git-Commit, kein PR)"] }), _jsxs("label", { style: { display: "flex", gap: 8, alignItems: "center", cursor: "pointer", fontSize: 13, color: "var(--text)" }, children: [_jsx("input", { type: "checkbox", checked: noPr, onChange: e => setNoPr(e.target.checked) }), "Ohne PR erstellen (--no-pr)"] })] }), _jsxs("div", { style: { display: "flex", gap: 8, justifyContent: "flex-end" }, children: [_jsx("button", { onClick: () => setShowModal(false), children: "Abbrechen" }), _jsx("button", { className: "primary", disabled: starting, onClick: handleExecute, children: starting ? "Startet…" : "Execute" })] })] }) }))] }));
}
function AttemptSummary({ attempts, status, issueUrl }) {
    const lastPr = [...attempts].reverse().find(a => a.pr_url)?.pr_url;
    const failed = attempts.filter(a => a.error);
    return (_jsxs("div", { style: { marginTop: 8, fontSize: 12, display: "flex", flexDirection: "column", gap: 4 }, children: [lastPr && (_jsxs("span", { children: ["PR: ", _jsx("a", { href: lastPr, target: "_blank", rel: "noreferrer", style: { color: "var(--accent)" }, children: lastPr })] })), status === "labeled" || status === "merged" ? (_jsxs("span", { style: { color: "var(--green)" }, children: ["Pass-Rate: ", formatRate(attempts), " \u00B7 ", attempts.length, " Attempt(s) \u00B7 Status: implemented"] })) : status === "dry_run" ? (_jsxs("span", { style: { color: "var(--yellow)" }, children: ["Dry-run \u2014 ", attempts[0]?.explanation ?? "keine Erklärung"] })) : status === "aborted" ? (_jsx("span", { style: { color: "var(--yellow)" }, children: "Manuell abgebrochen" })) : (_jsxs(_Fragment, { children: [failed.map(a => (_jsxs("span", { style: { color: "var(--red)" }, children: ["Attempt ", a.attempt, ": ", a.error?.slice(0, 120)] }, a.attempt))), issueUrl && (_jsxs("span", { children: ["Issue: ", _jsx("a", { href: issueUrl, target: "_blank", rel: "noreferrer", style: { color: "var(--red)" }, children: issueUrl })] }))] }))] }));
}
function lineColor(line) {
    if (line.includes("✓"))
        return "#b8bb26";
    if (line.includes("✗") || /fehler|error|fail/i.test(line))
        return "#fb4934";
    if (/läuft|generiert|attempt|erstellt|committed|PR/i.test(line))
        return "#fabd2f";
    return "#ebdbb2";
}
function formatRate(attempts) {
    const rates = attempts.map(a => a.eval_pass_rate).filter((r) => r !== null);
    if (!rates.length)
        return "—";
    return `${Math.round(rates[rates.length - 1] * 100)} %`;
}
function panelBorder(status) {
    if (status === "running")
        return "var(--accent)";
    if (status === "labeled" || status === "merged")
        return "var(--green)";
    if (status === "dry_run" || status === "aborted")
        return "var(--yellow)";
    return "var(--red)";
}
function statusIcon(status) {
    if (status === "running")
        return "⚙";
    if (status === "labeled" || status === "merged")
        return "✓";
    if (status === "dry_run")
        return "🔍";
    if (status === "aborted")
        return "⊘";
    return "✗";
}
function statusTitle(run, specId) {
    if (run.status === "running") {
        const current = run.attempts.length + 1;
        const max = run.max_attempts ?? 3;
        return `Pipeline läuft — ${specId} · Attempt ${current}/${max}`;
    }
    if (run.status === "labeled")
        return "Implementiert — PR erstellt";
    if (run.status === "merged")
        return "Implementiert — PR gemergt";
    if (run.status === "dry_run")
        return "Dry-run abgeschlossen";
    if (run.status === "aborted")
        return "Pipeline abgebrochen";
    return `Pipeline fehlgeschlagen — ${run.attempts.length} Attempt(s)`;
}
const modalOverlay = {
    position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
    display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100,
};
const modalBox = {
    background: "var(--surface)", border: "1px solid var(--border)",
    borderRadius: "var(--radius)", padding: 24, width: 440, maxWidth: "90vw",
};
