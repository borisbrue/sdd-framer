import { createContext, useCallback, useContext, useState } from "react";

export interface Toast {
  id: string;
  message: string;
  type: "success" | "error" | "info";
}

interface NotificationCtx {
  toasts: Toast[];
  notify: (message: string, type?: Toast["type"]) => void;
  dismiss: (id: string) => void;
}

const NotificationContext = createContext<NotificationCtx>({
  toasts: [],
  notify: () => {},
  dismiss: () => {},
});

let _seq = 0;

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const notify = useCallback((message: string, type: Toast["type"] = "info") => {
    const id = `toast-${++_seq}`;
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => dismiss(id), 5000);
  }, [dismiss]);

  return (
    <NotificationContext.Provider value={{ toasts, notify, dismiss }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </NotificationContext.Provider>
  );
}

export function useNotify() {
  return useContext(NotificationContext).notify;
}

// ─── Toast UI ─────────────────────────────────────────────────────────────────

const TYPE_COLOR: Record<Toast["type"], string> = {
  success: "var(--green)",
  error:   "var(--red)",
  info:    "var(--accent)",
};

const TYPE_ICON: Record<Toast["type"], string> = {
  success: "✓",
  error:   "✕",
  info:    "ℹ",
};

function ToastContainer({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: string) => void }) {
  if (toasts.length === 0) return null;
  return (
    <div style={{
      position: "fixed",
      top: 16,
      right: 16,
      zIndex: 9999,
      display: "flex",
      flexDirection: "column",
      gap: 8,
      maxWidth: 360,
    }}>
      {toasts.map(t => (
        <div
          key={t.id}
          style={{
            background: "var(--surface)",
            border: `1px solid ${TYPE_COLOR[t.type]}`,
            borderLeft: `4px solid ${TYPE_COLOR[t.type]}`,
            borderRadius: 6,
            padding: "10px 14px",
            display: "flex",
            gap: 10,
            alignItems: "flex-start",
            boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
          }}
        >
          <span style={{ color: TYPE_COLOR[t.type], fontWeight: 700, flexShrink: 0 }}>
            {TYPE_ICON[t.type]}
          </span>
          <span style={{ fontSize: 13, flex: 1, lineHeight: 1.4 }}>{t.message}</span>
          <button
            onClick={() => onDismiss(t.id)}
            style={{ background: "none", border: "none", color: "var(--muted)", cursor: "pointer", padding: 0, fontSize: 14, lineHeight: 1, flexShrink: 0 }}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
