import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef } from "react";
import QRCode from "qrcode";
export default function QrCodeOverlay({ payload, onClose }) {
    const canvasRef = useRef(null);
    useEffect(() => {
        if (!canvasRef.current)
            return;
        const json = JSON.stringify({ sdd: payload.sdd, name: payload.name, url: payload.url, token: payload.token });
        QRCode.toCanvas(canvasRef.current, json, {
            width: 280,
            margin: 2,
            color: { dark: "#000000", light: "#ffffff" },
        }).catch(console.error);
    }, [payload]);
    function handleBackdrop(e) {
        if (e.target === e.currentTarget)
            onClose();
    }
    return (_jsx("div", { onClick: handleBackdrop, style: {
            position: "fixed", inset: 0,
            background: "rgba(0,0,0,0.7)",
            display: "flex", alignItems: "center", justifyContent: "center",
            zIndex: 1000,
        }, children: _jsxs("div", { style: {
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                padding: 24,
                display: "flex", flexDirection: "column", alignItems: "center", gap: 16,
                maxWidth: 340,
            }, children: [_jsx("h3", { style: { margin: 0, color: "var(--accent)", fontSize: 15 }, children: "Mit PWA verbinden" }), _jsx("div", { style: {
                        background: "#fff",
                        padding: 12,
                        borderRadius: 8,
                        display: "inline-block",
                        lineHeight: 0,
                    }, children: _jsx("canvas", { ref: canvasRef }) }), _jsxs("div", { style: { textAlign: "center", fontSize: 12, color: "var(--muted)", lineHeight: 1.5 }, children: [_jsx("div", { style: { fontWeight: 600, color: "var(--text)", marginBottom: 4 }, children: payload.name }), _jsx("div", { style: { fontFamily: "monospace", wordBreak: "break-all" }, children: payload.url }), _jsx("div", { style: { marginTop: 6, color: "var(--yellow)" }, children: "Token wird nach dem Scan sofort rotiert." })] }), _jsx("button", { onClick: onClose, style: { width: "100%" }, children: "Schliessen" })] }) }));
}
