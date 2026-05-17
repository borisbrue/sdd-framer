import { useEffect, useState } from "react";
import { api, Contract, SpecDetail as SpecDetailType, Test } from "../api";
import AiPanel from "./AiPanel";
import AnalyzePanel from "./AnalyzePanel";
import ExecutePanel from "./ExecutePanel";
import LogPanel from "./LogPanel";
import TestRunPanel from "./TestRunPanel";
import ContractForm from "./ContractForm";
import IdChip from "./IdChip";
import MarkdownBody from "./MarkdownBody";
import OpenButton from "./OpenButton";
import TestForm from "./TestForm";

interface Props {
  specId: string;
  contracts: Contract[];
  tests: Test[];
  onNavigate: (id: string) => void;
  onRefresh: () => void;
}

export default function SpecDetail({ specId, contracts, tests, onNavigate, onRefresh }: Props) {
  const [detail, setDetail] = useState<SpecDetailType | null>(null);
  const [showContractForm, setShowContractForm] = useState(false);
  const [showTestForm, setShowTestForm] = useState(false);

  useEffect(() => {
    setDetail(null);
    api.getSpec(specId).then(setDetail).catch(console.error);
  }, [specId]);

  if (!detail) return <div style={{ padding: 20, color: "var(--muted)" }}>Lade…</div>;

  const myContracts = contracts.filter((c) => c.spec === specId);
  const myTests = tests.filter((t) => t.spec === specId);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Execute Flow (nur bei status=approved) */}
      <ExecutePanel
        spec={detail}
        onStatusChange={() => {
          api.getSpec(specId).then(setDetail).catch(console.error);
          onRefresh();
        }}
      />

      {/* Header */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
              <code style={{ color: "var(--accent)", fontSize: 13 }}>{detail.id}</code>
              <span className={`badge badge-${detail.status}`}>{detail.status}</span>
              {detail.priority !== "medium" && (
                <span style={{ fontSize: 11, color: "var(--yellow)" }}>{detail.priority}</span>
              )}
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>{detail.title}</h2>
            <div style={{ display: "flex", gap: 16, fontSize: 12, color: "var(--muted)", flexWrap: "wrap" }}>
              {detail.project && (
                <span>Projekt: <code style={{ color: "var(--yellow)", fontSize: 11, background: "var(--surface)", padding: "1px 6px", borderRadius: 4 }}>{detail.project}</code></span>
              )}
              {detail.owner && <span>Owner: <strong style={{ color: "var(--text)" }}>{detail.owner}</strong></span>}
              {detail.version && <span>v{detail.version}</span>}
              {detail.created && <span>Erstellt: {detail.created}</span>}
              {detail.tags.length > 0 && (
                <span>{detail.tags.map(t => <code key={t} style={{ marginLeft: 4, background: "var(--surface)", padding: "1px 5px", borderRadius: 4 }}>{t}</code>)}</span>
              )}
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

      {/* Verknüpfungen */}
      {(detail.depends_on.length > 0) && (
        <section className="card">
          <h3 style={sectionHead}>Hängt ab von</h3>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
            {detail.depends_on.map(id => <IdChip key={id} id={id} onClick={onNavigate} />)}
          </div>
        </section>
      )}

      {/* Contracts */}
      <section>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <h3 style={sectionHead}>Contracts ({myContracts.length})</h3>
          <button onClick={() => setShowContractForm(v => !v)}>+ Contract</button>
        </div>
        {showContractForm && (
          <ContractForm specId={specId} onCreated={() => { setShowContractForm(false); onRefresh(); }} onCancel={() => setShowContractForm(false)} />
        )}
        {myContracts.length === 0 && !showContractForm
          ? <p style={{ color: "var(--red)", fontSize: 13 }}>⚠ Kein Contract – Spec kann nicht validiert werden.</p>
          : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {myContracts.map(c => (
                <div key={c.id} className="card" style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}
                  onClick={() => onNavigate(c.id)}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <IdChip id={c.id} onClick={onNavigate} />
                    <span style={{ fontSize: 13 }}>{c.title}</span>
                    <code style={{ fontSize: 11, color: "var(--muted)" }}>[{c.format}]</code>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 11, color: "var(--muted)" }}>{c.tests.length} Tests</span>
                    <OpenButton absFile={c.abs_file} label="↗" />
                  </div>
                </div>
              ))}
            </div>
          )}
      </section>

      {/* Tests */}
      <section>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <h3 style={sectionHead}>Tests ({myTests.length})</h3>
          <button onClick={() => setShowTestForm(v => !v)} disabled={myContracts.length === 0}>+ Test</button>
        </div>
        {showTestForm && (
          <TestForm specId={specId} contracts={myContracts} onCreated={() => { setShowTestForm(false); onRefresh(); }} onCancel={() => setShowTestForm(false)} />
        )}
        {myTests.length === 0 && !showTestForm
          ? <p style={{ color: "var(--red)", fontSize: 13 }}>⚠ Kein Test angelegt.</p>
          : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {myTests.map(t => (
                <div key={t.id} className="card" style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}
                  onClick={() => onNavigate(t.id)}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <IdChip id={t.id} onClick={onNavigate} />
                    <span style={{ fontSize: 13 }}>{t.title}</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 11, color: "var(--muted)" }}>{t.level}</span>
                    <OpenButton absFile={t.abs_file} label="↗" />
                  </div>
                </div>
              ))}
            </div>
          )}
      </section>

      {/* Test Results */}
      <TestRunPanel specId={specId} />

      {/* Live Container Logs (SPEC-0022) */}
      <LogPanel specId={specId} />

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
        docType="spec"
      />

      {/* KI-Assistent */}
      <AiPanel
        specId={detail.id}
        specContent={detail.body}
        onNavigate={onNavigate}
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
