import { useCallback, useEffect, useMemo, useState } from "react";
import { api, Contract, Test, AiUsageEntry } from "../api";
import { useNotify } from "./NotificationContext";
import MarkdownBody from "./MarkdownBody";
import AnalyzePanel from "./AnalyzePanel";
import ApprovePanel from "./ApprovePanel";
import ContractSuggestPanel from "./ContractSuggestPanel";
import TestSuggestPanel from "./TestSuggestPanel";
import IdChip from "./IdChip";
import OpenButton from "./OpenButton";

// ── Section helpers ────────────────────────────────────────────────────────────

interface Section { key: string; heading: string; content: string; }

function parseSections(body: string): Section[] {
  const lines = body.split("\n");
  if (lines.length > 0 && lines[lines.length - 1] === "") lines.pop();
  const sections: Section[] = [];
  let current: Section = { key: "pre", heading: "", content: "" };
  let idx = 0;
  for (const line of lines) {
    if (/^#{1,3} /.test(line)) {
      sections.push(current);
      current = { key: `s${idx++}`, heading: line, content: "" };
    } else {
      current.content += line + "\n";
    }
  }
  sections.push(current);
  return sections.filter((s, i) => i > 0 || s.heading || s.content.trim());
}

function sectionsToBody(sections: Section[]): string {
  return sections.map(s => (s.heading ? s.heading + "\n" + s.content : s.content)).join("");
}

function extractToc(body: string): string {
  return body.split("\n").filter(l => /^#{1,3} /.test(l)).join("\n");
}

// ── Types ──────────────────────────────────────────────────────────────────────

// Phase 1: spec → Phase 2: analyse → Phase 3: review-confirm → Phase 4: contracts → Phase 5: contract-review → Phase 6: tests
type WizardPhase = "spec" | "analyse" | "review-confirm" | "contracts" | "contract-review" | "tests";

interface StepDef {
  num: number;
  label: string;
  type: "text" | "readonly";
  instruction: string;
}

// ── Phase bar definitions ──────────────────────────────────────────────────────

const PHASES: { key: WizardPhase; label: string }[] = [
  { key: "spec",            label: "Spec" },
  { key: "analyse",         label: "Qualitätsprüfung" },
  { key: "review-confirm",  label: "Review" },
  { key: "contracts",       label: "Contracts" },
  { key: "contract-review", label: "Contract-Review" },
  { key: "tests",           label: "Tests" },
];

// ── Spec steps (sections 1–7, 10, 11; sections 8+9 handled by later phases) ───

const SPEC_STEPS: StepDef[] = [
  { num: 1,  label: "Kontext",  type: "text",     instruction: "Beschreibe Ist-Zustand, Problem und Motivation in 3–5 Sätzen." },
  { num: 2,  label: "Ziel",     type: "text",     instruction: "Erarbeite Primärziel, messbare Erfolgskriterien und Nicht-Ziele." },
  { num: 3,  label: "Stories",  type: "text",     instruction: "Erstelle passende User Stories als Tabelle (ID | Als ... | möchte ich ... | um ...)." },
  { num: 4,  label: "FR",       type: "text",     instruction: "Definiere klare, testbare Funktionale Anforderungen als Liste (FR-01, FR-02, ...)." },
  { num: 5,  label: "NFR",      type: "text",     instruction: "Fülle die NFR-Tabelle aus: Performance, Security, Accessibility, Observability, Datenschutz." },
  { num: 6,  label: "Gherkin",  type: "text",     instruction: "Schreibe Gherkin-Szenarien (Given/When/Then) für alle Funktionalen Anforderungen." },
  { num: 7,  label: "Fehler",   type: "text",     instruction: "Liste relevante Edge Cases und Fehlerfälle auf." },
  { num: 10, label: "Fragen",   type: "text",     instruction: "Identifiziere offene Fragen, die vor der Implementierung geklärt werden müssen." },
  { num: 11, label: "Historie", type: "readonly", instruction: "" },
];

const SECTION_TITLES: Record<number, string> = {
  1: "Kontext & Motivation", 2: "Zielsetzung", 3: "User Stories",
  4: "Funktionale Anforderungen", 5: "Nicht-funktionale Anforderungen",
  6: "Akzeptanzkriterien (Gherkin)", 7: "Edge Cases & Fehlerfälle",
  10: "Offene Fragen", 11: "Änderungshistorie",
};

// Derive a sensible starting phase based on spec status + existing artifacts
function deriveInitialPhase(status: string, contracts: Contract[], tests: Test[]): WizardPhase {
  if (status !== "review") return "spec";
  if (tests.length > 0) return "tests";
  if (contracts.length > 0) return "contract-review";
  return "contracts";
}

// ── ContractReviewCard ─────────────────────────────────────────────────────────

function ContractReviewCard({
  contract, onNavigate,
}: { contract: Contract; onNavigate: (id: string) => void }) {
  const [body, setBody] = useState<string | null>(null);

  useEffect(() => {
    api.getContract(contract.id)
      .then(d => setBody((d as { body?: string }).body ?? ""))
      .catch(() => setBody(""));
  }, [contract.id]);

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <IdChip id={contract.id} onClick={onNavigate} />
          <span style={{ fontSize: 13, fontWeight: 600 }}>{contract.title}</span>
          <code style={{ fontSize: 11, color: "var(--muted)" }}>[{contract.format}]</code>
        </div>
        <OpenButton absFile={contract.abs_file} label="↗" />
      </div>
      {body === null ? (
        <p style={{ fontSize: 12, color: "var(--muted)" }}>Lade…</p>
      ) : (
        <AnalyzePanel
          docId={contract.id}
          docContent={body}
          docType="contract"
          autoTrigger={true}
          onSaveBody={async (newBody) => {
            await api.patchContractBody(contract.id, newBody);
            setBody(newBody);
          }}
        />
      )}
    </div>
  );
}

function UsagePill({ entry }: { entry: AiUsageEntry }) {
  return (
    <span style={{ fontSize: 10, color: "var(--muted)", fontFamily: "monospace" }}>
      {entry.provider === "claude-cli"
        ? "claude-cli"
        : `${entry.input_tokens}↑ ${entry.output_tokens}↓ $${(entry.cost_usd ?? 0).toFixed(5)}`}
    </span>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

interface Props {
  specId: string;
  specStatus: string;
  initialBody: string;
  contracts: Contract[];
  tests: Test[];
  onSaved: (newBody: string) => void;
  onNavigate: (id: string) => void;
  onRefresh: () => void;
  onRequestReview: () => Promise<void>;
  onApproved: () => void;
}

export default function SpecWizard({
  specId, specStatus, initialBody, contracts, tests,
  onSaved, onNavigate, onRefresh, onRequestReview, onApproved,
}: Props) {
  const notify = useNotify();

  // phase initialises once; not re-derived when specStatus prop changes later
  const [phase, setPhase] = useState<WizardPhase>(
    () => deriveInitialPhase(specStatus, contracts, tests),
  );
  const [specStep, setSpecStep]           = useState(0);
  const [sections, setSections]           = useState<Section[]>(() => parseSections(initialBody));
  const [saving, setSaving]               = useState(false);
  const [analyseTrigger, setAnalyseTrigger] = useState(0);
  const [confirmingReview, setConfirmingReview] = useState(false);

  // AI assist state for current spec section
  const [aiPhase, setAiPhase]   = useState<"idle" | "generating" | "preview">("idle");
  const [aiPreview, setAiPreview] = useState("");
  const [aiUsage, setAiUsage]   = useState<AiUsageEntry | null>(null);
  const [isEditing, setIsEditing] = useState(false);

  const step        = SPEC_STEPS[specStep];
  const currentBody = useMemo(() => sectionsToBody(sections), [sections]);
  const specToc     = useMemo(() => extractToc(currentBody), [currentBody]);

  const sectionIndex = useMemo(
    () => step ? sections.findIndex(s => s.heading.match(new RegExp(`^## ${step.num}\\.`))) : -1,
    [sections, step],
  );
  const currentContent = sectionIndex >= 0 ? sections[sectionIndex].content : "";

  const updateContent = (v: string) => {
    if (sectionIndex < 0) return;
    setSections(prev => prev.map((s, i) => i === sectionIndex ? { ...s, content: v } : s));
  };

  const saveToServer = useCallback(async () => {
    setSaving(true);
    try {
      const body = sectionsToBody(sections);
      await api.updateSpec(specId, body);
      onSaved(body);
    } catch (e) {
      notify(e instanceof Error ? e.message : "Fehler beim Speichern", "error");
    } finally {
      setSaving(false);
    }
  }, [sections, specId, onSaved, notify]);

  const enterPhase = async (next: WizardPhase) => {
    if (phase === "spec") await saveToServer();
    setPhase(next);
    setAiPhase("idle");
    setAiPreview("");
    setAiUsage(null);
    setIsEditing(false);
    if (next === "analyse") setAnalyseTrigger(k => k + 1);
  };

  const handleGenerate = async () => {
    if (aiPhase === "generating" || !step?.instruction) return;
    setAiPhase("generating");
    setAiPreview("");
    try {
      const res = await api.aiImproveSection({
        spec_id: specId,
        section_heading: `## ${step.num}.`,
        section_content: currentContent,
        instructions: step.instruction,
        full_spec_content: specToc,
        linked_spec_ids: [],
      });
      setAiPreview(res.result);
      setAiUsage(res.usage);
      setAiPhase("preview");
    } catch (e) {
      notify(e instanceof Error ? e.message : "Fehler beim Generieren", "error");
      setAiPhase("idle");
    }
  };

  const handleAccept = () => {
    updateContent(aiPreview.trimEnd() + "\n");
    setAiPhase("idle");
    setAiPreview("");
    setAiUsage(null);
  };

  const handleReviewConfirm = async () => {
    setConfirmingReview(true);
    try {
      await onRequestReview();
      setPhase("contracts");
    } catch (e) {
      notify(e instanceof Error ? e.message : "Fehler beim Review", "error");
    } finally {
      setConfirmingReview(false);
    }
  };

  // ── Phase bar ───────────────────────────────────────────────────────────────

  const phaseIdx = PHASES.findIndex(p => p.key === phase);

  const phaseBar = (
    <div style={{ display: "flex", alignItems: "center", gap: 0, marginBottom: 20, flexWrap: "wrap" }}>
      {PHASES.map((p, i) => {
        const isCurrent = p.key === phase;
        const isPast    = i < phaseIdx;
        return (
          <div key={p.key} style={{ display: "flex", alignItems: "center" }}>
            <div style={{
              fontSize: 11, padding: "4px 12px", borderRadius: 4,
              border: `1px solid ${isCurrent ? "var(--accent)" : isPast ? "var(--green)" : "var(--border)"}`,
              background: isCurrent ? "var(--accent)" : "transparent",
              color: isCurrent ? "#1e1e2e" : isPast ? "var(--green)" : "var(--muted)",
              fontWeight: isCurrent ? 700 : 400,
            }}>
              {isPast ? "✓ " : ""}{p.label}
            </div>
            {i < PHASES.length - 1 && (
              <span style={{ fontSize: 11, color: "var(--border)", padding: "0 4px" }}>→</span>
            )}
          </div>
        );
      })}
    </div>
  );

  // ── Spec step bar ───────────────────────────────────────────────────────────

  const stepBar = (
    <div style={{ display: "flex", gap: 3, flexWrap: "wrap", marginBottom: 14 }}>
      {SPEC_STEPS.map((s, i) => {
        const isCurrent = i === specStep;
        const isPast    = i < specStep;
        return (
          <button key={i}
            onClick={async () => {
              if (!isCurrent) {
                await saveToServer();
                setSpecStep(i);
                setAiPhase("idle");
                setAiPreview("");
                setIsEditing(false);
              }
            }}
            style={{
              fontSize: 10, padding: "3px 8px", borderRadius: 4,
              border: `1px solid ${isCurrent ? "var(--accent)" : "var(--border)"}`,
              background: isCurrent ? "var(--accent)" : isPast ? "var(--surface)" : "transparent",
              color: isCurrent ? "#1e1e2e" : "var(--muted)",
              cursor: isCurrent ? "default" : "pointer",
              fontWeight: isCurrent ? 700 : 400,
            }}>
            {isPast ? "✓ " : `${s.num}. `}{s.label}
          </button>
        );
      })}
    </div>
  );

  // ── Spec section edit card ──────────────────────────────────────────────────

  const specCard = step && (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ fontSize: 15, fontWeight: 700 }}>
          {step.num}. {SECTION_TITLES[step.num] ?? step.label}
        </h3>
        {aiUsage && <UsagePill entry={aiUsage} />}
      </div>

      {aiPhase === "preview" && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 10, color: "var(--accent)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 6 }}>
            ✦ KI-Vorschlag
          </div>
          <div style={{
            padding: "10px 12px", borderRadius: 4,
            background: "var(--bg)", border: "1px solid var(--accent)", marginBottom: 8,
          }}>
            <MarkdownBody markdown={aiPreview} onIdClick={onNavigate} />
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={() => { setAiPhase("idle"); setAiPreview(""); setAiUsage(null); }}>
              ✗ Verwerfen
            </button>
            <button className="primary" onClick={handleAccept}>✓ Übernehmen</button>
            <button onClick={handleGenerate} style={{ color: "var(--accent)", borderColor: "var(--accent)" }}>
              ↺ Neu
            </button>
          </div>
        </div>
      )}

      {aiPhase !== "preview" && (
        <>
          {isEditing ? (
            <textarea
              autoFocus
              value={currentContent}
              onChange={e => updateContent(e.target.value)}
              onBlur={() => setIsEditing(false)}
              rows={Math.max(4, currentContent.split("\n").length + 1)}
              style={{
                width: "100%", fontFamily: "monospace", fontSize: 12, display: "block",
                background: "var(--bg)", color: "var(--text)", border: "1px solid var(--accent)",
                borderRadius: 4, padding: 8, resize: "vertical", boxSizing: "border-box",
              }}
            />
          ) : (
            <div
              onClick={() => step.type !== "readonly" && setIsEditing(true)}
              style={{ cursor: step.type !== "readonly" ? "text" : "default", minHeight: 40 }}
              title={step.type !== "readonly" ? "Klicken zum Bearbeiten" : undefined}>
              {currentContent.trim()
                ? <MarkdownBody markdown={currentContent} onIdClick={onNavigate} />
                : <span style={{ color: "var(--muted)", fontSize: 12, fontStyle: "italic" }}>
                    Noch kein Inhalt — hier klicken oder KI-Vorschlag nutzen
                  </span>}
            </div>
          )}
          {step.type === "text" && (
            <div style={{ display: "flex", gap: 8, marginTop: 12, paddingTop: 10, borderTop: "1px solid var(--border)" }}>
              <button onClick={() => setIsEditing(v => !v)} style={{ fontSize: 11, padding: "2px 10px" }}>
                {isEditing ? "Vorschau" : "✏ Bearbeiten"}
              </button>
              <button
                onClick={handleGenerate}
                disabled={aiPhase === "generating"}
                style={{ fontSize: 11, padding: "2px 10px", color: "var(--accent)", borderColor: "var(--accent)" }}>
                {aiPhase === "generating" ? "✦ …" : "✦ KI-Vorschlag"}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );

  // ── Navigation footer ───────────────────────────────────────────────────────

  const isLastStep = specStep === SPEC_STEPS.length - 1;

  const nav = (() => {
    if (phase === "spec") return (
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <button
          onClick={async () => { await saveToServer(); setSpecStep(s => s - 1); setAiPhase("idle"); setIsEditing(false); }}
          disabled={specStep === 0 || saving}>
          ← Zurück
        </button>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={saveToServer} disabled={saving}>
            {saving ? "Speichert…" : "💾 Speichern"}
          </button>
          {isLastStep ? (
            <button className="primary" onClick={() => enterPhase("analyse")} disabled={saving}>
              Qualitätsprüfung →
            </button>
          ) : (
            <button className="primary"
              onClick={async () => { await saveToServer(); setSpecStep(s => s + 1); setAiPhase("idle"); setIsEditing(false); }}
              disabled={saving}>
              Weiter →
            </button>
          )}
        </div>
      </div>
    );

    if (phase === "analyse") return (
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <button onClick={() => setPhase("spec")}>← Zurück zur Spec</button>
        <button className="primary" onClick={() => setPhase("review-confirm")}>
          Review des Spec →
        </button>
      </div>
    );

    if (phase === "review-confirm") return null; // buttons are inline in phase content

    if (phase === "contracts") return (
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <button onClick={() => setPhase("review-confirm")}>← Zurück</button>
        <button
          className="primary"
          onClick={() => setPhase("contract-review")}
          disabled={contracts.length === 0}
          title={contracts.length === 0 ? "Mindestens einen Contract anlegen" : undefined}>
          Contracts prüfen →
        </button>
      </div>
    );

    if (phase === "contract-review") return (
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <button onClick={() => setPhase("contracts")}>← Zurück</button>
        <button className="primary" onClick={() => setPhase("tests")}>Tests anlegen →</button>
      </div>
    );

    if (phase === "tests") return (
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <button onClick={() => setPhase("contract-review")}>← Zurück</button>
      </div>
    );
  })();

  // ── Phase content ───────────────────────────────────────────────────────────

  const phaseContent = (() => {
    // Phase 1: Spec sections
    if (phase === "spec") return (
      <>
        {stepBar}
        {specCard}
      </>
    );

    // Phase 2: KI-Qualitätsprüfung
    if (phase === "analyse") return (
      <div className="card">
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>Qualitätsprüfung</h3>
        <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 14 }}>
          Die KI analysiert die Spec auf Vollständigkeit und Widersprüche.
          Arbeite die Findings ein, bevor du die Spec in Review setzt.
        </p>
        <AnalyzePanel
          docId={specId}
          docContent={currentBody}
          docType="spec"
          forceStartKey={analyseTrigger}
          onSaveBody={async (newBody) => {
            await api.updateSpec(specId, newBody);
            setSections(parseSections(newBody));
            onSaved(newBody);
          }}
        />
      </div>
    );

    // Phase 3: Review-Bestätigung (zwischen 2 und 3 des Flows)
    if (phase === "review-confirm") return (
      <div className="card">
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 8 }}>Review des Spec</h3>
        <p style={{ fontSize: 13, color: "var(--muted)", lineHeight: 1.6, marginBottom: 16 }}>
          Die Spec wurde analysiert und überarbeitet. Setze sie jetzt in den Review-Status —
          danach werden Contracts auf Basis der Anforderungen angelegt.
        </p>
        <div style={{
          padding: "10px 14px", borderRadius: 6,
          background: "var(--surface)", border: "1px solid var(--border)", marginBottom: 20,
        }}>
          <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 6, textTransform: "uppercase", letterSpacing: 0.8 }}>
            Checkliste
          </div>
          <ul style={{ fontSize: 12, color: "var(--text)", paddingLeft: 16, lineHeight: 1.9, margin: 0 }}>
            <li>Sektionen 1–7 ausgefüllt und vollständig</li>
            <li>Qualitätsprüfung-Findings eingearbeitet</li>
            <li>Offene Fragen (Sektion 10) dokumentiert</li>
          </ul>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={() => setPhase("analyse")}>← Zurück zur Qualitätsprüfung</button>
          <button className="primary" onClick={handleReviewConfirm} disabled={confirmingReview}>
            {confirmingReview ? "Setze in Review…" : "✓ Spec in Review setzen & Contracts anlegen →"}
          </button>
        </div>
      </div>
    );

    // Phase 4: Contracts anlegen
    if (phase === "contracts") return (
      <div className="card">
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 6 }}>Contracts anlegen</h3>
        <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 14 }}>
          Die KI schlägt Contracts vor, die sich aus den Anforderungen ergeben.
          Jeder Contract wird nach dem Anlegen automatisch befüllt.
        </p>
        {contracts.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 14 }}>
            {contracts.map(c => (
              <div key={c.id} className="card"
                style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}
                onClick={() => onNavigate(c.id)}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <IdChip id={c.id} onClick={onNavigate} />
                  <span style={{ fontSize: 13 }}>{c.title}</span>
                  <code style={{ fontSize: 11, color: "var(--muted)" }}>[{c.format}]</code>
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <span style={{ fontSize: 11, color: "var(--muted)" }}>{c.tests.length} Tests</span>
                  <OpenButton absFile={c.abs_file} label="↗" />
                </div>
              </div>
            ))}
          </div>
        )}
        <ContractSuggestPanel specId={specId} specContent={currentBody} onCreated={onRefresh} />
      </div>
    );

    // Phase 5: Contract-Review (unabhängig per Contract)
    if (phase === "contract-review") return (
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{
          padding: "10px 14px", background: "var(--surface)",
          borderRadius: 6, border: "1px solid var(--border)",
        }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Contract-Review</h3>
          <p style={{ fontSize: 12, color: "var(--muted)" }}>
            Jeder Contract wird unabhängig geprüft. Findings können direkt behoben werden.
          </p>
        </div>
        {contracts.length === 0 ? (
          <p style={{ fontSize: 12, color: "var(--yellow)", padding: "8px 0" }}>
            ⚠ Noch keine Contracts vorhanden. Gehe zurück und lege Contracts an.
          </p>
        ) : (
          contracts.map(c => <ContractReviewCard key={c.id} contract={c} onNavigate={onNavigate} />)
        )}
      </div>
    );

    // Phase 6: Tests anlegen (pro Contract) + Freigabe
    if (phase === "tests") return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div className="card">
          <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 6 }}>Tests anlegen</h3>
          <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 14 }}>
            Jeder Test prüft genau einen Contract. Die KI schlägt Tests vor und befüllt sie nach dem Anlegen.
          </p>
          {tests.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 14 }}>
              {tests.map(t => (
                <div key={t.id} className="card"
                  style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}
                  onClick={() => onNavigate(t.id)}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <IdChip id={t.id} onClick={onNavigate} />
                    <span style={{ fontSize: 13 }}>{t.title}</span>
                  </div>
                  <span style={{ fontSize: 11, color: "var(--muted)" }}>{t.level}</span>
                </div>
              ))}
            </div>
          )}
          {contracts.length === 0 ? (
            <p style={{ fontSize: 12, color: "var(--yellow)" }}>⚠ Noch keine Contracts vorhanden.</p>
          ) : (
            <TestSuggestPanel
              specId={specId} specContent={currentBody}
              contracts={contracts} onCreated={onRefresh}
            />
          )}
        </div>

        <div className="card">
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>Spec freigeben</h3>
          <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 12 }}>
            Wenn alle Contracts und Tests angelegt und geprüft sind, kann die Spec freigegeben werden.
          </p>
          <ApprovePanel specId={specId} onApproved={onApproved} />
        </div>
      </div>
    );
  })();

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {phaseBar}
      {phaseContent}
      {nav}
    </div>
  );
}
