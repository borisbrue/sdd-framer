import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { createContext, useCallback, useContext, useState } from "react";
const NotificationContext = createContext({
    toasts: [],
    notify: () => { },
    dismiss: () => { },
});
let _seq = 0;
export function NotificationProvider({ children }) {
    const [toasts, setToasts] = useState([]);
    const dismiss = useCallback((id) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    }, []);
    const notify = useCallback((message, type = "info") => {
        const id = `toast-${++_seq}`;
        setToasts(prev => [...prev, { id, message, type }]);
        setTimeout(() => dismiss(id), 5000);
    }, [dismiss]);
    return (_jsxs(NotificationContext.Provider, { value: { toasts, notify, dismiss }, children: [children, _jsx(ToastContainer, { toasts: toasts, onDismiss: dismiss })] }));
}
export function useNotify() {
    return useContext(NotificationContext).notify;
}
// ─── Toast UI ─────────────────────────────────────────────────────────────────
const TYPE_COLOR = {
    success: "var(--green)",
    error: "var(--red)",
    info: "var(--accent)",
};
const TYPE_ICON = {
    success: "✓",
    error: "✕",
    info: "ℹ",
};
function ToastContainer({ toasts, onDismiss }) {
    if (toasts.length === 0)
        return null;
    return (_jsx("div", { style: {
            position: "fixed",
            top: 16,
            right: 16,
            zIndex: 9999,
            display: "flex",
            flexDirection: "column",
            gap: 8,
            maxWidth: 360,
        }, children: toasts.map(t => (_jsxs("div", { style: {
                background: "var(--surface)",
                border: `1px solid ${TYPE_COLOR[t.type]}`,
                borderLeft: `4px solid ${TYPE_COLOR[t.type]}`,
                borderRadius: 6,
                padding: "10px 14px",
                display: "flex",
                gap: 10,
                alignItems: "flex-start",
                boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
            }, children: [_jsx("span", { style: { color: TYPE_COLOR[t.type], fontWeight: 700, flexShrink: 0 }, children: TYPE_ICON[t.type] }), _jsx("span", { style: { fontSize: 13, flex: 1, lineHeight: 1.4 }, children: t.message }), _jsx("button", { onClick: () => onDismiss(t.id), style: { background: "none", border: "none", color: "var(--muted)", cursor: "pointer", padding: 0, fontSize: 14, lineHeight: 1, flexShrink: 0 }, children: "\u00D7" })] }, t.id))) }));
}
