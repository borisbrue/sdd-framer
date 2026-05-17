import { useEffect, useState } from "react";
import { api, TestDetail as TestDetailType } from "../api";
import IdChip from "./IdChip";
import MarkdownBody from "./MarkdownBody";
import OpenButton from "./OpenButton";

interface Props {
  testId: string;
  onNavigate: (id: string) => void;
}

const LEVEL_COLORS: Record<string, string> = {
  unit:         "#cba6f7",
  integration:  "#89dceb",
  contract:     "var(--green)",
  acceptance:   "var(--accent)",
  performance:  "var(--yellow)",
  property:     "#f5c2e7",
};

export default function TestDetail({ testId, onNavigate }: Props) {
  const [detail, setDetail] = useState<TestDetailType | null>(null);

  useEffect(() => {
    setDetail(null);
    api.getTest(testId).then(setDetail).catch(console.error);
  }, [testId]);

  if (!detail) return <div style={{ padding: 20, color: "var(--muted)" }}>Lade…</div>;

  const levelColor = LEVEL_COLORS[detail.level] ?? "var(--muted)";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
              <code style={{ color: "#cba6f7", fontSize: 13 }}>{detail.id}</code>
              <span className={`badge badge-${detail.status}`}>{detail.status}</span>
              <span style={{ fontSize: 11, color: levelColor, border: `1px solid ${levelColor}`, padding: "1px 8px", borderRadius: 999 }}>
                {detail.level}
              </span>
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>{detail.title}</h2>
            <div style={{ display: "flex", gap: 12, fontSize: 12, color: "var(--muted)", flexWrap: "wrap", alignItems: "center" }}>
              <span>Spec: <IdChip id={detail.spec} onClick={onNavigate} /></span>
              <span>Contract: <IdChip id={detail.contract} onClick={onNavigate} /></span>
              {detail.framework && <span>Framework: <strong style={{ color: "var(--text)" }}>{detail.framework}</strong></span>}
              {detail.version && <span>v{detail.version}</span>}
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
            <OpenButton absFile={detail.abs_file} />
          </div>
        </div>
        <div style={{ marginTop: 10, fontSize: 11, color: "var(--muted)" }}>
          <code>{detail.file}</code>
        </div>
      </div>

      {/* Markdown Body */}
      {detail.body.trim() && (
        <section className="card">
          <h3 style={{ fontSize: 12, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 12 }}>Inhalt</h3>
          <MarkdownBody markdown={detail.body} onIdClick={onNavigate} />
        </section>
      )}
    </div>
  );
}
