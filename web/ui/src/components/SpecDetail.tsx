import { useEffect, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { api, Contract, Holdout, SpecDetail as SpecDetailType, Test } from "../api";
import AiPanel from "./AiPanel";
import AnalyzePanel from "./AnalyzePanel";
import SpecWizard from "./SpecWizard";
import RestructurePanel from "./RestructurePanel";
import ExecutePanel from "./ExecutePanel";
import LogPanel from "./LogPanel";
import TaskKanbanBoard from "./TaskKanbanBoard";
import TestRunPanel from "./TestRunPanel";
import ContractForm from "./ContractForm";
import ContractSuggestPanel from "./ContractSuggestPanel";
import TestSuggestPanel from "./TestSuggestPanel";
import IdChip from "./IdChip";
import MarkdownBody from "./MarkdownBody";
import OpenButton from "./OpenButton";
import SpecPipelineView from "./SpecPipelineView";
import TestForm from "./TestForm";

const sectionHead: CSSProperties = {
  fontSize: 12,
  color: "var(--muted)",
  textTransform: "uppercase",
  letterSpacing: 1,
};

function Collapsible({ title, children, defaultOpen = false }: {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section>
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          display: "flex", alignItems: "center", gap: 6, width: "100%",
          background: "none", border: "none", cursor: "pointer", padding: "4px 0",
        }}
      >
        <span style={{ fontSize: 11, color: "var(--muted)" }}>{open ? "▾" : "▸"}</span>
        <span style={sectionHead}>{title}</span>
      </button>
      {open && (
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 12 }}>
          {children}
        </div>
      )}
    </section>
  );
}

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
  const [holdouts, setHoldouts] = useState<Holdout[]>([]);
  const [analysisTrigger, setAnalysisTrigger] = useState(0);
  const [logConnectTrigger, setLogConnectTrigger] = useState(0);

  useEffect(() => {
    setDetail(null);
    api.getSpec(specId).then(setDetail).catch(console.error);
    api.getHoldouts(specId).then(d => setHoldouts(d.holdouts)).catch(() => setHoldouts([]));
  }, [specId]);

  if (!detail) return <div style={{ padding: 20, color: "var(--muted)" }}>Lade…</div>;

  const myContracts = contracts.filter(c => c.spec === specId);
  const myTests = tests.filter(t => t.spec === specId);

  const isDraft = detail.status === "draft";
  const isReview = detail.status === "review";
  const inWorkPhase = detail.status === "active";
  const inExecPhase = detail.status === "approved" || detail.status === "in-progress" || detail.status === "implemented";
  const hasKanban = detail.status === "in-progress" || detail.status === "implemented";

  // ── Shared render helpers (no hooks) ──────────────────────────────────────

  const header = (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <code style={{ color: "var(--accent)", fontSize: 13 }}>{detail.id}</code>
            <select
              value={detail.status}
              onChange={async e => {
                const s = e.target.value;
                if (s === "approved") return;
                await api.patchSpecStatus(detail.id, s);
                setDetail(d => d ? { ...d, status: s } : d);
                onRefresh();
              }}
              style={{
                fontSize: 11, background: "var(--surface)", color: "var(--muted)",
                border: "1px solid var(--border)", borderRadius: 4, padding: "2px 6px", cursor: "pointer",
              }}
            >
              <option value="draft">draft</option>
              <option value="active">active</option>
              <option value="review">review</option>
              <option value="approved" disabled>approved (nur via Gate)</option>
              <option value="in-progress" disabled>in-progress</option>
              <option value="implemented" disabled>implemented</option>
              <option value="deprecated">deprecated</option>
            </select>
            {detail.priority !== "medium" && (
              <span style={{ fontSize: 11, color: "var(--yellow)" }}>{detail.priority}</span>
            )}
          </div>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>{detail.title}</h2>
          <div style={{ display: "flex", gap: 16, fontSize: 12, color: "var(--muted)", flexWrap: "wrap" }}>
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
  );

  const pipeline = (
    <SpecPipelineView specId={specId} onActionTriggered={() => setLogConnectTrigger(k => k + 1)} />
  );

  const contractsSection = (withForms: boolean, withSuggest = false) => (
    <section>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <h3 style={sectionHead}>Contracts ({myContracts.length})</h3>
        {withForms && <button onClick={() => setShowContractForm(v => !v)}>+ Contract</button>}
      </div>
      {withForms && showContractForm && (
        <ContractForm specId={specId} onCreated={() => { setShowContractForm(false); onRefresh(); }} onCancel={() => setShowContractForm(false)} />
      )}
      {myContracts.length === 0
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
      {withSuggest && detail && (
        <ContractSuggestPanel specId={detail.id} specContent={detail.body} onCreated={onRefresh} />
      )}
    </section>
  );

  const testsSection = (withForms: boolean, withSuggest = false) => (
    <section>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <h3 style={sectionHead}>Tests ({myTests.length})</h3>
        {withForms && <button onClick={() => setShowTestForm(v => !v)} disabled={myContracts.length === 0}>+ Test</button>}
      </div>
      {withForms && showTestForm && (
        <TestForm specId={specId} contracts={myContracts} onCreated={() => { setShowTestForm(false); onRefresh(); }} onCancel={() => setShowTestForm(false)} />
      )}
      {myTests.length === 0
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
      {withSuggest && detail && myContracts.length > 0 && (
        <TestSuggestPanel
          specId={detail.id} specContent={detail.body}
          contracts={myContracts} onCreated={onRefresh}
        />
      )}
    </section>
  );

  const dependsOnSection = detail.depends_on.length > 0 && (
    <section className="card">
      <h3 style={sectionHead}>Hängt ab von</h3>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
        {detail.depends_on.map(id => <IdChip key={id} id={id} onClick={onNavigate} />)}
      </div>
    </section>
  );

  const holdoutsSection = holdouts.length > 0 && (
    <section>
      <h3 style={{ ...sectionHead, marginBottom: 8 }}>Holdout-Szenarien ({holdouts.length})</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {holdouts.map(h => (
          <div key={h.id} className="card"
            style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}
            onClick={() => onNavigate(h.id)}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <IdChip id={h.id} onClick={onNavigate} />
              <span style={{ fontSize: 13 }}>{h.title}</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 11, color: "var(--muted)" }}>{h.status}</span>
              <OpenButton absFile={h.abs_file} label="↗" />
            </div>
          </div>
        ))}
      </div>
    </section>
  );

  const wrap = (children: ReactNode) => (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>{children}</div>
  );

  // ── DRAFT: geführter Wizard ───────────────────────────────────────────────

  if (isDraft || isReview) return wrap(<>
    {header}
    <SpecWizard
      specId={detail.id}
      specStatus={detail.status}
      initialBody={detail.body}
      contracts={myContracts}
      tests={myTests}
      onSaved={newBody => setDetail(d => d ? { ...d, body: newBody } : d)}
      onNavigate={onNavigate}
      onRefresh={onRefresh}
      onRequestReview={async () => {
        await api.patchSpecStatus(detail.id, "review");
        setDetail(d => d ? { ...d, status: "review" } : d);
        onRefresh();
      }}
      onApproved={() => {
        setDetail(d => d ? { ...d, status: "approved" } : d);
        onRefresh();
      }}
    />
    {detail.depends_on.length > 0 && (
      <Collapsible title="Abhängigkeiten">{dependsOnSection}</Collapsible>
    )}
  </>);

  // ── WORK PHASE (active / review): Fokus auf Contracts, Tests, Freigabe ────

  if (inWorkPhase) return wrap(<>
    {header}
    {pipeline}
    {contractsSection(true, true)}
    {testsSection(true, true)}
    {dependsOnSection}
    {holdoutsSection}
    {detail.body.trim() && (
      <Collapsible title="Inhalt" defaultOpen>
        <section className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={sectionHead}>Inhalt</h3>
            <RestructurePanel
              docId={detail.id} docType="spec" docContent={detail.body}
              onRestructured={newBody => { setDetail(d => d ? { ...d, body: newBody } : d); setAnalysisTrigger(k => k + 1); }}
            />
          </div>
          <MarkdownBody markdown={detail.body} onIdClick={onNavigate} />
        </section>
      </Collapsible>
    )}
    <Collapsible title="✦ KI-Werkzeuge">
      <AnalyzePanel
        docId={detail.id} docContent={detail.body} docType="spec" forceStartKey={analysisTrigger}
        onSaveBody={async (newBody) => {
          await api.updateSpec(detail.id, newBody);
          setDetail(d => d ? { ...d, body: newBody } : d);
        }}
      />
      <AiPanel specId={detail.id} specContent={detail.body} onNavigate={onNavigate} />
    </Collapsible>
  </>);

  // ── EXEC PHASE (approved / in-progress / implemented): Fokus auf Monitoring

  if (inExecPhase) return wrap(<>
    {header}
    <ExecutePanel
      spec={detail}
      onStatusChange={() => { api.getSpec(specId).then(setDetail).catch(console.error); onRefresh(); }}
    />
    {pipeline}
    {hasKanban && (
      <section className="card">
        <h3 style={sectionHead}>Tasks</h3>
        <TaskKanbanBoard specId={specId} />
      </section>
    )}
    <TestRunPanel specId={specId} />
    <LogPanel specId={specId} autoConnectTrigger={logConnectTrigger} />
    {holdoutsSection}
    {detail.body.trim() && (
      <Collapsible title="Inhalt" defaultOpen>
        <section className="card">
          <MarkdownBody markdown={detail.body} onIdClick={onNavigate} />
        </section>
      </Collapsible>
    )}
    <Collapsible title={`Contracts & Tests (${myContracts.length} / ${myTests.length})`}>
      {contractsSection(false)}
      {testsSection(false)}
    </Collapsible>
    <Collapsible title="✦ KI-Werkzeuge">
      <AnalyzePanel
        docId={detail.id} docContent={detail.body} docType="spec" forceStartKey={analysisTrigger}
        onSaveBody={async (newBody) => {
          await api.updateSpec(detail.id, newBody);
          setDetail(d => d ? { ...d, body: newBody } : d);
        }}
      />
      <AiPanel specId={detail.id} specContent={detail.body} onNavigate={onNavigate} />
    </Collapsible>
  </>);

  // ── DEPRECATED (und Fallback): Lesbare Dokumentation ─────────────────────

  return wrap(<>
    {header}
    <div style={{
      padding: "10px 14px", background: "var(--surface)", borderRadius: 6,
      border: "1px solid var(--border)", fontSize: 12, color: "var(--muted)",
    }}>
      Diese Spec ist archiviert und wird nicht mehr aktiv gepflegt.
    </div>
    {detail.body.trim() && (
      <section className="card">
        <MarkdownBody markdown={detail.body} onIdClick={onNavigate} />
      </section>
    )}
    <Collapsible title={`Contracts & Tests (${myContracts.length} / ${myTests.length})`}>
      {contractsSection(false)}
      {testsSection(false)}
    </Collapsible>
    {detail.depends_on.length > 0 && (
      <Collapsible title="Abhängigkeiten">{dependsOnSection}</Collapsible>
    )}
  </>);
}
