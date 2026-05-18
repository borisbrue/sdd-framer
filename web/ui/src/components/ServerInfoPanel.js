import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { api } from "../api";
import QrCodeOverlay from "./QrCodeOverlay";
export default function ServerInfoPanel({ onClose }) {
    const [info, setInfo] = useState(null);
    const [qrPayload, setQrPayload] = useState(null);
    const [loadingQr, setLoadingQr] = useState(false);
    const [generatingToken, setGeneratingToken] = useState(false);
    const [rawPayload, setRawPayload] = useState(null);
    const [error, setError] = useState("");
    useEffect(() => {
        api.serverInfo()
            .then(setInfo)
            .catch(() => setError("Server-Info konnte nicht geladen werden."));
    }, []);
    async function handleGenerateToken() {
        setGeneratingToken(true);
        setError("");
        try {
            await api.generateToken();
            const updated = await api.serverInfo();
            setInfo(updated);
        }
        catch (e) {
            if (e instanceof Error && e.message !== "token_already_exists") {
                setError("Token konnte nicht generiert werden.");
            }
        }
        finally {
            setGeneratingToken(false);
        }
    }
    async function handleShowQr() {
        setLoadingQr(true);
        setError("");
        try {
            const payload = await api.qrPayload();
            setQrPayload(payload);
        }
        catch (e) {
            if (e instanceof Error && e.message === "no_token_configured") {
                setError("Kein Token konfiguriert. Starte mit --external-url und füge pwa.auth.token zu config.yaml hinzu.");
            }
            else if (e instanceof Error && e.message === "no_external_url_configured") {
                setError("Keine externe URL gesetzt. Starte den Server mit --external-url <url>.");
            }
            else {
                setError("QR-Code konnte nicht generiert werden.");
            }
        }
        finally {
            setLoadingQr(false);
        }
    }
    return (_jsxs(_Fragment, { children: [_jsx("div", { style: {
                    position: "fixed", inset: 0,
                    background: "rgba(0,0,0,0.5)",
                    display: "flex", alignItems: "flex-start", justifyContent: "flex-end",
                    zIndex: 900,
                    paddingTop: 52, paddingRight: 12,
                }, onClick: (e) => { if (e.target === e.currentTarget)
                    onClose(); }, children: _jsxs("div", { style: {
                        background: "var(--surface)",
                        border: "1px solid var(--border)",
                        borderRadius: 10,
                        padding: 20,
                        minWidth: 280,
                        maxWidth: 360,
                        display: "flex", flexDirection: "column", gap: 14,
                    }, children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center" }, children: [_jsx("span", { style: { fontWeight: 700, color: "var(--accent)", fontSize: 14 }, children: "Server-Info" }), _jsx("button", { onClick: onClose, style: { padding: "2px 8px", fontSize: 13 }, children: "\u00D7" })] }), !info && !error && (_jsx("p", { style: { color: "var(--muted)", fontSize: 13, margin: 0 }, children: "Laden\u2026" })), error && (_jsx("p", { style: { color: "var(--red)", fontSize: 12, margin: 0 }, children: error })), info && (_jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 8 }, children: [_jsx(Row, { label: "Projekt", value: info.name }), _jsx(Row, { label: "Externe URL", value: info.externalUrl || _jsx("span", { style: { color: "var(--muted)", fontStyle: "italic" }, children: "nicht konfiguriert" }) }), _jsx(Row, { label: "Token", value: info.tokenHash
                                        ? _jsxs("span", { style: { fontFamily: "monospace" }, children: [info.tokenHash, "\u2026"] })
                                        : _jsx("span", { style: { color: "var(--muted)", fontStyle: "italic" }, children: "kein Token" }) })] })), info && !info.tokenHash && (_jsx("button", { onClick: handleGenerateToken, disabled: generatingToken, style: { width: "100%" }, children: generatingToken ? "Generiere…" : "Token generieren" })), _jsxs("div", { style: { display: "flex", gap: 8 }, children: [_jsx("button", { onClick: handleShowQr, disabled: loadingQr || !info?.externalUrl || !info?.tokenHash, className: "primary", style: { flex: 1 }, title: !info?.externalUrl ? "Starte den Server mit --external-url" : undefined, children: loadingQr ? "Generiere…" : "QR-Code" }), _jsx("button", { onClick: async () => {
                                        if (rawPayload) {
                                            setRawPayload(null);
                                            return;
                                        }
                                        try {
                                            const p = await api.qrPayload();
                                            setRawPayload(p);
                                        }
                                        catch (e) {
                                            setError(e instanceof Error ? e.message : "Fehler");
                                        }
                                    }, disabled: !info?.externalUrl || !info?.tokenHash, style: { flex: 1 }, children: rawPayload ? "Ausblenden" : "Manuell" })] }), rawPayload && (_jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 6 }, children: [_jsx(CopyRow, { label: "URL", value: rawPayload.url }), _jsx(CopyRow, { label: "Token", value: rawPayload.token, mono: true })] })), _jsx("p", { style: { color: "var(--muted)", fontSize: 11, margin: 0, lineHeight: 1.4 }, children: "Der Token wird nach dem Scan / Verbinden sofort rotiert." })] }) }), qrPayload && (_jsx(QrCodeOverlay, { payload: qrPayload, onClose: () => setQrPayload(null) }))] }));
}
function Row({ label, value }) {
    return (_jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 2 }, children: [_jsx("span", { style: { fontSize: 10, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.5 }, children: label }), _jsx("span", { style: { fontSize: 13, color: "var(--text)", wordBreak: "break-all" }, children: value })] }));
}
function CopyRow({ label, value, mono }) {
    const [copied, setCopied] = useState(false);
    return (_jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 2 }, children: [_jsx("span", { style: { fontSize: 10, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.5 }, children: label }), _jsxs("div", { style: { display: "flex", gap: 6, alignItems: "center" }, children: [_jsx("span", { style: {
                            fontSize: 11, color: "var(--text)", wordBreak: "break-all", flex: 1,
                            fontFamily: mono ? "monospace" : undefined,
                            background: "var(--surface-2, #161b22)", padding: "4px 6px", borderRadius: 4,
                        }, children: value }), _jsx("button", { onClick: () => { navigator.clipboard.writeText(value); setCopied(true); setTimeout(() => setCopied(false), 1500); }, style: { flexShrink: 0, padding: "3px 8px", fontSize: 11 }, children: copied ? "✓" : "Kopieren" })] })] }));
}
