import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef, useState, useCallback } from "react";
// ── ANSI-to-HTML (basic 16-color + bold + reset) ──────────────────────────────
const FG = {
    30: "#555555", 31: "#cc3333", 32: "#33aa33", 33: "#aaaa22",
    34: "#3366cc", 35: "#aa33aa", 36: "#22aaaa", 37: "#cccccc",
    90: "#888888", 91: "#ff5555", 92: "#55ff55", 93: "#ffff55",
    94: "#5555ff", 95: "#ff55ff", 96: "#55ffff", 97: "#ffffff",
};
function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function ansiToHtml(raw) {
    const safe = escapeHtml(raw);
    const parts = [];
    let openSpan = false;
    let openBold = false;
    let pos = 0;
    const re = /\x1b\[(\d*(?:;\d*)*)m/g;
    let m;
    while ((m = re.exec(safe)) !== null) {
        parts.push(safe.slice(pos, m.index));
        pos = m.index + m[0].length;
        const codes = m[1].split(";").map(Number);
        for (const code of codes) {
            if (code === 0 || code === 39) {
                if (openBold) {
                    parts.push("</strong>");
                    openBold = false;
                }
                if (openSpan) {
                    parts.push("</span>");
                    openSpan = false;
                }
            }
            else if (code === 1) {
                if (!openBold) {
                    parts.push("<strong>");
                    openBold = true;
                }
            }
            else if (FG[code]) {
                if (openSpan)
                    parts.push("</span>");
                parts.push(`<span style="color:${FG[code]}">`);
                openSpan = true;
            }
        }
    }
    parts.push(safe.slice(pos));
    if (openBold)
        parts.push("</strong>");
    if (openSpan)
        parts.push("</span>");
    return parts.join("");
}
// ── WebSocket URL from current host ──────────────────────────────────────────
function wsUrl(specId) {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    return `${proto}//${host}/ws/logs/${specId}`;
}
let _lineId = 0;
export default function LogPanel({ specId, autoConnectTrigger }) {
    const [lines, setLines] = useState([]);
    const [conn, setConn] = useState("disconnected");
    const [autoScroll, setAutoScroll] = useState(true);
    const bottomRef = useRef(null);
    const wsRef = useRef(null);
    const autoScrollRef = useRef(true);
    autoScrollRef.current = autoScroll;
    const disconnect = useCallback(() => {
        if (wsRef.current) {
            wsRef.current.onclose = null;
            wsRef.current.close();
            wsRef.current = null;
        }
        setConn("disconnected");
    }, []);
    const connect = useCallback(() => {
        if (wsRef.current)
            return;
        setConn("connecting");
        setLines([]);
        const ws = new WebSocket(wsUrl(specId));
        wsRef.current = ws;
        ws.onopen = () => setConn("connected");
        ws.onmessage = (ev) => {
            try {
                const msg = JSON.parse(ev.data);
                if (msg.error === "no_stream") {
                    setConn("no_stream");
                    ws.close();
                    return;
                }
                const display = {
                    id: ++_lineId,
                    ts: msg.ts,
                    html: ansiToHtml(msg.line),
                    buffered: msg.buffered ?? false,
                    truncated: msg.truncated ?? false,
                };
                setLines(prev => prev.length >= 2000 ? [...prev.slice(-1999), display] : [...prev, display]);
            }
            catch {
                // ignore malformed messages
            }
        };
        ws.onerror = () => setConn("error");
        ws.onclose = () => {
            wsRef.current = null;
            setConn(prev => (prev === "no_stream" ? "no_stream" : "disconnected"));
        };
    }, [specId]);
    // Auto-scroll on new lines
    useEffect(() => {
        if (autoScrollRef.current && bottomRef.current) {
            bottomRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
        }
    }, [lines]);
    // Auto-connect when a pipeline action triggers it
    useEffect(() => {
        if (!autoConnectTrigger)
            return;
        if (wsRef.current) {
            wsRef.current.onclose = null;
            wsRef.current.close();
            wsRef.current = null;
        }
        setLines([]);
        // Small delay so the backend can mark the stream active before we connect
        setTimeout(connect, 400);
    }, [autoConnectTrigger, connect]);
    // Cleanup on unmount / specId change
    useEffect(() => {
        return () => {
            if (wsRef.current) {
                wsRef.current.onclose = null;
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [specId]);
    const connColor = {
        disconnected: "var(--muted)",
        connecting: "var(--yellow)",
        connected: "var(--green, #33aa33)",
        no_stream: "var(--muted)",
        error: "var(--red)",
    };
    const connLabel = {
        disconnected: "Getrennt",
        connecting: "Verbinde…",
        connected: "Live",
        no_stream: "Kein aktiver Stream",
        error: "Verbindungsfehler",
    };
    return (_jsxs("section", { className: "card", style: { padding: 0, overflow: "hidden" }, children: [_jsxs("div", { style: {
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "8px 14px",
                    borderBottom: "1px solid var(--border)",
                    background: "var(--surface)",
                }, children: [_jsx("span", { style: { fontSize: 12, fontWeight: 600, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1 }, children: "Container Logs" }), _jsxs("span", { style: { fontSize: 11, color: connColor[conn] }, children: ["\u25CF ", connLabel[conn]] }), _jsx("div", { style: { flex: 1 } }), _jsxs("label", { style: { fontSize: 11, color: "var(--muted)", display: "flex", alignItems: "center", gap: 4, cursor: "pointer" }, children: [_jsx("input", { type: "checkbox", checked: autoScroll, onChange: e => setAutoScroll(e.target.checked), style: { cursor: "pointer" } }), "Auto-Scroll"] }), conn === "connected" || conn === "connecting" ? (_jsx("button", { onClick: disconnect, style: { fontSize: 11, padding: "3px 10px" }, children: "Trennen" })) : (_jsx("button", { onClick: connect, style: { fontSize: 11, padding: "3px 10px" }, children: "Verbinden" })), _jsx("button", { onClick: () => setLines([]), disabled: lines.length === 0, style: { fontSize: 11, padding: "3px 10px" }, children: "Leeren" })] }), _jsxs("div", { onScroll: e => {
                    const el = e.currentTarget;
                    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
                    setAutoScroll(atBottom);
                }, style: {
                    height: 360,
                    overflowY: "auto",
                    background: "#0d1117",
                    fontFamily: "monospace",
                    fontSize: 12,
                    lineHeight: 1.5,
                    padding: "8px 14px",
                }, children: [lines.length === 0 && conn !== "connecting" && (_jsx("div", { style: { color: "#555", paddingTop: 8 }, children: conn === "no_stream"
                            ? "Kein aktiver Log-Stream. Starte den Container mit 'sdd dev up SPEC-XXXX'."
                            : conn === "disconnected"
                                ? "Klicke 'Verbinden' um Container-Logs live zu sehen."
                                : "Warte auf Log-Zeilen…" })), lines.map(l => (_jsxs("div", { style: { display: "flex", gap: 10, opacity: l.buffered ? 0.7 : 1 }, children: [_jsx("span", { style: { color: "#444", flexShrink: 0, userSelect: "none", fontSize: 10, paddingTop: 2 }, children: l.ts.slice(11, 23) }), _jsx("span", { style: { color: "#c9d1d9", wordBreak: "break-all", whiteSpace: "pre-wrap" }, dangerouslySetInnerHTML: { __html: l.html } }), l.truncated && (_jsx("span", { style: { color: "#664", flexShrink: 0 }, title: "Zeile wurde auf 4 KB gek\u00FCrzt", children: "\u2026" }))] }, l.id))), _jsx("div", { ref: bottomRef })] }), lines.length > 0 && (_jsxs("div", { style: {
                    fontSize: 10,
                    color: "var(--muted)",
                    padding: "3px 14px",
                    borderTop: "1px solid var(--border)",
                    display: "flex",
                    justifyContent: "space-between",
                }, children: [_jsxs("span", { children: [lines.filter(l => l.buffered).length, " gepuffert / ", lines.filter(l => !l.buffered).length, " live"] }), _jsxs("span", { children: [lines.length, " Zeilen gesamt"] })] }))] }));
}
