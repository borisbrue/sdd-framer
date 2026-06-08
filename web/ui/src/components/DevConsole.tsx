import { useEffect, useRef, useState } from "react";

interface LogEntry {
  ts: string;
  level: string;
  name: string;
  msg: string;
}

const LEVEL_COLOR: Record<string, string> = {
  DEBUG:    "var(--muted)",
  INFO:     "var(--text)",
  WARNING:  "var(--yellow)",
  ERROR:    "var(--red)",
  CRITICAL: "var(--red)",
};

interface Props {
  onClose: () => void;
}

export default function DevConsole({ onClose }: Props) {
  const [lines, setLines] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const [filter, setFilter] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource("/api/devlog/stream");
    esRef.current = es;

    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (e) => {
      try {
        const entry: LogEntry = JSON.parse(e.data as string);
        setLines(prev => [...prev.slice(-499), entry]);
      } catch {
        // ignore malformed
      }
    };

    return () => { es.close(); };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  const visible = filter
    ? lines.filter(l => l.msg.toLowerCase().includes(filter.toLowerCase()) || l.name.includes(filter))
    : lines;

  return (
    <div style={{
      position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 1000,
      background: "#0d0d14", borderTop: "1px solid var(--border)",
      display: "flex", flexDirection: "column",
      height: 260,
    }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "4px 12px", borderBottom: "1px solid var(--border)",
        background: "var(--surface)", flexShrink: 0,
      }}>
        <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1 }}>
          Konsole
        </span>
        <span style={{
          fontSize: 9, padding: "1px 5px", borderRadius: 999,
          background: connected ? "var(--green)" : "var(--red)",
          color: "#1e1e2e",
        }}>
          {connected ? "live" : "getrennt"}
        </span>
        <input
          value={filter}
          onChange={e => setFilter(e.target.value)}
          placeholder="Filter…"
          style={{
            flex: 1, maxWidth: 200, fontSize: 11, padding: "2px 6px",
            background: "var(--bg)", color: "var(--text)",
            border: "1px solid var(--border)", borderRadius: 4,
          }}
        />
        <span style={{ fontSize: 11, color: "var(--muted)", marginLeft: "auto" }}>
          {lines.length} Zeilen
        </span>
        <button
          onClick={() => setLines([])}
          style={{ fontSize: 11, padding: "2px 8px", color: "var(--muted)" }}
        >
          Leeren
        </button>
        <button
          onClick={onClose}
          style={{ fontSize: 13, padding: "1px 8px", color: "var(--muted)" }}
        >
          ×
        </button>
      </div>

      {/* Log lines */}
      <div style={{ flex: 1, overflowY: "auto", padding: "4px 0" }}>
        {visible.map((l, i) => (
          <div key={i} style={{
            display: "flex", gap: 8, padding: "1px 12px",
            fontFamily: "monospace", fontSize: 11, lineHeight: 1.5,
          }}>
            <span style={{ color: "var(--muted)", flexShrink: 0 }}>{l.ts}</span>
            <span style={{
              color: LEVEL_COLOR[l.level] ?? "var(--text)",
              flexShrink: 0, width: 50,
            }}>
              {l.level}
            </span>
            <span style={{ color: "var(--accent)", flexShrink: 0, maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {l.name}
            </span>
            <span style={{ color: LEVEL_COLOR[l.level] ?? "var(--text)", wordBreak: "break-all" }}>
              {l.msg}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
