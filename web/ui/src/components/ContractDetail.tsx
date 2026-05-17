import { useEffect, useState } from "react";
import { api, ContractDetail as ContractDetailType } from "../api";
import AnalyzePanel from "./AnalyzePanel";
import IdChip from "./IdChip";
import MarkdownBody from "./MarkdownBody";
import OpenButton from "./OpenButton";

interface Props {
  contractId: string;
  onNavigate: (id: string) => void;
}

export default function ContractDetail({ contractId, onNavigate }: Props) {
  const [detail, setDetail] = useState<ContractDetailType | null>(null);

  useEffect(() => {
    setDetail(null);
    api.getContract(contractId).then(setDetail).catch(console.error);
  }, [contractId]);

  if (!detail) return <div style={{ padding: 20, color: "var(--muted)" }}>Lade…</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
              <code style={{ color: "var(--green)", fontSize: 13 }}>{detail.id}</code>
              <span className={`badge badge-${detail.status}`}>{detail.status}</span>
              <code style={{ fontSize: 11, color: "var(--muted)" }}>[{detail.format}]</code>
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>{detail.title}</h2>
            <div style={{ display: "flex", gap: 12, fontSize: 12, color: "var(--muted)", flexWrap: "wrap" }}>
              <span>Spec: <IdChip id={detail.spec} onClick={onNavigate} /></span>
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

      {/* Tests */}
      {detail.tests.length > 0 && (
        <section className="card">
          <h3 style={sectionHead}>Tests</h3>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
            {detail.tests.map(id => <IdChip key={id} id={id} onClick={onNavigate} />)}
          </div>
        </section>
      )}

      {/* Artifact */}
      {detail.artifact_content && (
        <section className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <h3 style={sectionHead}>Artifact: <code style={{ color: "var(--accent)" }}>{detail.artifact}</code></h3>
            <OpenButton absFile={detail.abs_artifact} label="Artifact öffnen" />
          </div>
          <pre style={{ background: "var(--bg)", borderRadius: 6, padding: 12, fontSize: 12, overflowX: "auto", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
            {detail.artifact_content}
          </pre>
        </section>
      )}

      {/* Markdown Body */}
      {detail.body.trim() && (
        <section className="card">
          <h3 style={{ ...sectionHead, marginBottom: 12 }}>Inhalt</h3>
          <MarkdownBody markdown={detail.body} onIdClick={onNavigate} />
        </section>
      )}

      {/* KI-Analyse */}
      <AnalyzePanel
        docId={detail.id}
        docContent={detail.body}
        docType="contract"
      />
    </div>
  );
}

const sectionHead: React.CSSProperties = {
  fontSize: 12,
  color: "var(--muted)",
  textTransform: "uppercase",
  letterSpacing: 1,
};
