import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useCallback, useEffect, useState } from "react";
// ── Icons ──────────────────────────────────────────────────────────────────────
function StatusIcon({ status }) {
    const size = 22;
    if (status === "done")
        return (_jsxs("svg", { width: size, height: size, viewBox: "0 0 22 22", children: [_jsx("circle", { cx: "11", cy: "11", r: "10", fill: "var(--green)", opacity: "0.2", stroke: "var(--green)", strokeWidth: "1.5" }), _jsx("polyline", { points: "6,11 9.5,14.5 16,8", stroke: "var(--green)", strokeWidth: "2", fill: "none", strokeLinecap: "round", strokeLinejoin: "round" })] }));
    if (status === "active")
        return (_jsxs("svg", { width: size, height: size, viewBox: "0 0 22 22", children: [_jsx("circle", { cx: "11", cy: "11", r: "10", fill: "var(--accent)", opacity: "0.15", stroke: "var(--accent)", strokeWidth: "1.5" }), _jsx("circle", { cx: "11", cy: "11", r: "3.5", fill: "var(--accent)" })] }));
    if (status === "failed")
        return (_jsxs("svg", { width: size, height: size, viewBox: "0 0 22 22", children: [_jsx("circle", { cx: "11", cy: "11", r: "10", fill: "var(--red)", opacity: "0.15", stroke: "var(--red)", strokeWidth: "1.5" }), _jsx("line", { x1: "7", y1: "7", x2: "15", y2: "15", stroke: "var(--red)", strokeWidth: "2", strokeLinecap: "round" }), _jsx("line", { x1: "15", y1: "7", x2: "7", y2: "15", stroke: "var(--red)", strokeWidth: "2", strokeLinecap: "round" })] }));
    return (_jsx("svg", { width: size, height: size, viewBox: "0 0 22 22", children: _jsx("circle", { cx: "11", cy: "11", r: "10", fill: "transparent", stroke: "var(--border)", strokeWidth: "1.5" }) }));
}
function SubStatusDot({ status }) {
    const color = status === "done" ? "var(--green)"
        : status === "active" ? "var(--accent)"
            : status === "failed" ? "var(--red)"
                : "var(--border)";
    return (_jsx("span", { style: {
            display: "inline-block", width: 8, height: 8, borderRadius: "50%",
            background: color, flexShrink: 0,
        } }));
}
// ── Action button ──────────────────────────────────────────────────────────────
function ActionButton({ action, onDone, onTriggered }) {
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    if (action.info) {
        return (_jsx("span", { style: {
                fontSize: 11, color: "var(--muted)", fontFamily: "monospace",
                background: "var(--bg)", padding: "2px 8px", borderRadius: 4,
                border: "1px solid var(--border)",
            }, children: action.label }));
    }
    const trigger = async () => {
        if (!action.endpoint)
            return;
        setLoading(true);
        setResult(null);
        try {
            const res = await fetch(action.endpoint, { method: action.method ?? "POST" });
            const data = await res.json();
            if (!res.ok) {
                setResult("✗ " + (data.detail ?? `HTTP ${res.status}`));
                return;
            }
            if (data.ok) {
                setResult("✓ " + (data.output?.split("\n")[0] ?? "OK"));
                onTriggered?.(action.id);
                setTimeout(onDone, 1500);
            }
            else {
                const lines = (data.output ?? data.detail ?? "Fehler unbekannt")
                    .split("\n").filter(Boolean).slice(0, 4).join(" · ");
                setResult("✗ " + lines);
            }
        }
        catch (e) {
            setResult("✗ Verbindungsfehler: " + (e instanceof Error ? e.message : String(e)));
        }
        finally {
            setLoading(false);
        }
    };
    return (_jsxs("div", { style: { display: "flex", alignItems: "center", gap: 8 }, children: [_jsx("button", { onClick: trigger, disabled: loading, style: action.secondary ? {
                    background: "none", color: "var(--muted)",
                    border: "1px solid var(--border)", borderRadius: 5, padding: "3px 10px",
                    fontSize: 11, fontWeight: 400, cursor: loading ? "wait" : "pointer",
                    opacity: loading ? 0.5 : 1,
                } : {
                    background: "var(--accent)", color: "var(--bg)",
                    border: "none", borderRadius: 5, padding: "4px 12px",
                    fontSize: 12, fontWeight: 600, cursor: loading ? "wait" : "pointer",
                    opacity: loading ? 0.7 : 1,
                }, children: loading ? "…" : action.label }), result && (_jsx("span", { style: {
                    fontSize: 11,
                    color: result.startsWith("✓") ? "var(--green)" : "var(--red)",
                }, children: result }))] }));
}
// ── Single stage node ──────────────────────────────────────────────────────────
function StageNode({ stage, onRefresh, onTriggered }) {
    const isActive = stage.status === "active";
    const isFailed = stage.status === "failed";
    return (_jsxs("div", { style: {
            display: "flex", flexDirection: "row", gap: 14, alignItems: "flex-start",
        }, children: [_jsx("div", { style: { display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }, children: _jsx(StatusIcon, { status: stage.status }) }), _jsxs("div", { style: {
                    flex: 1, paddingBottom: 4,
                    opacity: stage.status === "pending" ? 0.5 : 1,
                }, children: [_jsxs("div", { style: { display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }, children: [_jsx("span", { style: {
                                    fontWeight: isActive || isFailed ? 700 : 500,
                                    fontSize: 13,
                                    color: isFailed ? "var(--red)" : isActive ? "var(--text)" : "var(--text)",
                                }, children: stage.label }), stage.count !== undefined && stage.count > 0 && (_jsx("span", { style: {
                                    fontSize: 10, background: "var(--border)", color: "var(--muted)",
                                    borderRadius: 10, padding: "1px 6px",
                                }, children: stage.count }))] }), stage.detail && (_jsx("div", { style: { fontSize: 11, color: "var(--muted)", marginBottom: 4 }, children: stage.detail })), stage.substeps && stage.substeps.length > 0 && (_jsx("div", { style: { display: "flex", flexDirection: "column", gap: 3, marginBottom: 6 }, children: stage.substeps.map(sub => (_jsxs("div", { style: { display: "flex", alignItems: "center", gap: 6, fontSize: 11 }, children: [_jsx(SubStatusDot, { status: sub.status }), _jsx("span", { style: { color: sub.status === "pending" ? "var(--muted)" : "var(--text)" }, children: sub.label }), sub.detail && (_jsx("span", { style: { color: "var(--muted)", marginLeft: 4 }, children: sub.detail }))] }, sub.id))) })), stage.actions && stage.actions.length > 0 && (_jsx("div", { style: { display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }, children: stage.actions.map(a => (_jsx(ActionButton, { action: a, onDone: onRefresh, onTriggered: onTriggered }, a.id))) }))] })] }));
}
// ── Connector line ─────────────────────────────────────────────────────────────
function Connector({ fromStatus }) {
    return (_jsx("div", { style: {
            width: 2, height: 20, marginLeft: 10,
            background: fromStatus === "done" ? "var(--green)"
                : fromStatus === "active" ? "var(--accent)"
                    : "var(--border)",
            opacity: fromStatus === "pending" ? 0.3 : 0.6,
            borderRadius: 1,
        } }));
}
// ── Main component ─────────────────────────────────────────────────────────────
const LOG_ACTION_IDS = new Set(["start", "run-tests", "review", "propose-contracts", "generate-holdouts", "finalize", "evaluate"]);
export default function SpecPipelineView({ specId, onActionTriggered }) {
    const [state, setState] = useState(null);
    const [error, setError] = useState(null);
    const load = useCallback(() => {
        fetch(`/api/specs/${specId}/pipeline`)
            .then(r => r.ok ? r.json() : r.json().then((e) => { throw new Error(e.detail); }))
            .then(setState)
            .catch(e => setError(e.message));
    }, [specId]);
    useEffect(() => {
        load();
        // Poll every 15s when a stage is active
        const interval = setInterval(() => {
            if (state?.stages.some(s => s.status === "active"))
                load();
        }, 15000);
        return () => clearInterval(interval);
    }, [load, state]);
    if (error)
        return (_jsxs("div", { style: { padding: 12, color: "var(--muted)", fontSize: 12 }, children: ["Pipeline nicht verf\u00FCgbar: ", error] }));
    if (!state)
        return (_jsx("div", { style: { padding: 12, color: "var(--muted)", fontSize: 12 }, children: "Lade Pipeline\u2026" }));
    return (_jsxs("div", { className: "card", style: { padding: "16px 20px" }, children: [_jsxs("div", { style: {
                    display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16,
                }, children: [_jsx("span", { style: { fontWeight: 700, fontSize: 13, color: "var(--text)" }, children: "Pipeline" }), _jsx("button", { onClick: load, style: {
                            background: "none", border: "none", cursor: "pointer",
                            color: "var(--muted)", fontSize: 11, padding: "2px 6px",
                        }, title: "Aktualisieren", children: "\u21BB" })] }), _jsx("div", { style: { display: "flex", flexDirection: "column" }, children: state.stages.map((stage, i) => (_jsxs("div", { children: [_jsx(StageNode, { stage: stage, onRefresh: load, onTriggered: id => LOG_ACTION_IDS.has(id) && onActionTriggered?.(id) }), i < state.stages.length - 1 && (_jsx("div", { style: { marginLeft: 10 }, children: _jsx(Connector, { fromStatus: stage.status }) }))] }, stage.id))) }), state.next_action && (_jsxs("div", { style: {
                    marginTop: 16, padding: "10px 14px",
                    background: "var(--bg)", border: "1px solid var(--border)",
                    borderRadius: 6, display: "flex", alignItems: "center", gap: 10,
                }, children: [_jsx("span", { style: { fontSize: 11, color: "var(--muted)", flexShrink: 0 }, children: "N\u00E4chster Schritt" }), _jsx(ActionButton, { action: state.next_action, onDone: load, onTriggered: id => LOG_ACTION_IDS.has(id) && onActionTriggered?.(id) })] })), _jsxs("div", { style: { marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }, children: [state.container_running && (_jsx("span", { style: {
                            fontSize: 10, padding: "2px 8px", borderRadius: 10,
                            background: "rgba(180,210,100,0.15)", color: "var(--green)",
                            border: "1px solid var(--green)", opacity: 0.8,
                        }, children: "Container l\u00E4uft" })), state.holdout_count > 0 && (_jsxs("span", { style: {
                            fontSize: 10, padding: "2px 8px", borderRadius: 10,
                            background: "var(--surface)", color: "var(--muted)",
                            border: "1px solid var(--border)",
                        }, children: [state.holdout_count, " Holdout", state.holdout_count !== 1 ? "s" : ""] })), state.pr_path && (_jsx("span", { style: {
                            fontSize: 10, padding: "2px 8px", borderRadius: 10,
                            background: "rgba(100,150,255,0.1)", color: "var(--accent)",
                            border: "1px solid var(--accent)", opacity: 0.8,
                        }, children: "PR erstellt" }))] })] }));
}
