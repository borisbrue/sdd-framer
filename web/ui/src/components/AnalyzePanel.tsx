import { useEffect, useRef, useState } from "react";
import { api, AnalysisQuestion, AnalysisIssue, AnalysisSummary, PersistedAnalysis, AiUsageEntry } from "../api";
import { useNotify } from "./NotificationContext";

const AUTO_TRIGGER_DELAY_MS = 3000;
const POLL_INTERVAL_MS = 2000;

interface Props {
  docId: string;
  docContent: string;
  docType: "spec" | "contract";
  autoTrigger?: boolean;
  onBodySaved?: () => void;
  onSaveBody?: (newBody: string) => Promise<void>;
  forceStartKey?: number;
}

const SEVERITY_ICON: Record<string, string> = {
  error:      "🔴",
  warning:    "🟡",
  suggestion: "💡",
};

const SEVERITY_COLOR: Record<string, string> = {
  error:      "var(--red)",
  warning:    "var(--yellow)",
  suggestion: "var(--accent)",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

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

interface ChangedSection { heading: string; newContent: string; }

function getChangedSections(oldBody: string, newBody: string): ChangedSection[] {
  const oldSecs = parseSections(oldBody);
  const newSecs = parseSections(newBody);
  return newSecs
    .filter(ns => {
      const os = oldSecs.find(s => s.heading === ns.heading);
      return !os || os.content !== ns.content;
    })
    .map(ns => ({ heading: ns.heading, newContent: ns.content }));
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

// ─── FindingFixPanel ──────────────────────────────────────────────────────────

function FindingFixPanel({
  findingText,
  findingSection,
  docId,
  currentBody,
  onApplied,
  onDismiss,
}: {
  findingText: string;
  findingSection?: string;
  docId: string;
  currentBody: string;
  onApplied: (newBody: string) => void;
  onDismiss?: () => void;
}) {
  const [expanded, setExpanded]       = useState(false);
  const [instruction, setInstruction] = useState("");
  const [aiPhase, setAiPhase]         = useState<"idle" | "generating" | "preview">("idle");
  const [preview, setPreview]         = useState("");
  const [changed, setChanged]         = useState<ChangedSection[]>([]);
  const [usage, setUsage]             = useState<AiUsageEntry | null>(null);
  const [error, setError]             = useState("");

  const handleGenerate = async () => {
    if (aiPhase !== "idle") return;
    setAiPhase("generating");
    setError("");
    try {
      const res = await api.aiFixFinding({
        spec_id: docId,
        finding_text: findingText,
        finding_section: findingSection,
        full_spec_content: currentBody,
        instructions: instruction || undefined,
      });
      setPreview(res.result);
      setChanged(getChangedSections(currentBody, res.result));
      setUsage(res.usage);
      setAiPhase("preview");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler beim Generieren.");
      setAiPhase("idle");
    }
  };

  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        style={{ fontSize: 11, padding: "2px 8px", color: "var(--accent)", borderColor: "var(--accent)" }}
      >
        ✦ KI-Lösung
      </button>
    );
  }

  return (
    <div style={{ marginTop: 8, borderLeft: "2px solid var(--accent)", paddingLeft: 10 }}>
      {aiPhase !== "preview" && (
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <input
            value={instruction}
            onChange={e => setInstruction(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); handleGenerate(); } }}
            placeholder="Weitere Anweisungen (optional)…"
            disabled={aiPhase === "generating"}
            autoFocus
            style={{
              flex: 1, fontSize: 12, padding: "3px 8px",
              background: "var(--surface)", color: "var(--text)",
              border: "1px solid var(--border)", borderRadius: 4,
              opacity: aiPhase === "generating" ? 0.6 : 1,
            }}
          />
          <button
            onClick={handleGenerate}
            disabled={aiPhase === "generating"}
            style={{
              fontSize: 12, padding: "3px 10px", whiteSpace: "nowrap",
              background: "var(--accent)", color: "#1e1e2e",
              border: "none", borderRadius: 4, cursor: "pointer",
              opacity: aiPhase === "generating" ? 0.5 : 1,
            }}
          >
            {aiPhase === "generating" ? "✦ …" : "✦ Lösung generieren"}
          </button>
          <button
            onClick={() => setExpanded(false)}
            style={{ fontSize: 11, padding: "2px 6px" }}
          >
            ×
          </button>
        </div>
      )}

      {aiPhase === "preview" && (
        <div>
          <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 10, color: "var(--accent)", textTransform: "uppercase", letterSpacing: 0.8 }}>
              ✦ Vorgeschlagene Änderungen
            </span>
            {usage && <UsagePill entry={usage} />}
          </div>
          {changed.length > 0 ? changed.map((cs, i) => (
            <div key={i} style={{ marginBottom: 10 }}>
              {cs.heading && (
                <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text)", display: "block", marginBottom: 4 }}>
                  {cs.heading.replace(/^#{1,3}\s+/, "")}
                </span>
              )}
              <pre style={{
                fontSize: 11, background: "var(--bg)", border: "1px solid var(--accent)",
                borderRadius: 4, padding: 8, whiteSpace: "pre-wrap", wordBreak: "break-word",
                maxHeight: 200, overflowY: "auto", margin: 0,
              }}>
                {cs.newContent}
              </pre>
            </div>
          )) : (
            <p style={{ fontSize: 12, color: "var(--muted)" }}>
              Dokument vollständig überarbeitet — kein Abschnitts-Diff verfügbar.
            </p>
          )}
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <button
              onClick={() => { setAiPhase("idle"); setPreview(""); setChanged([]); setExpanded(false); }}
              style={{ fontSize: 11, padding: "2px 8px" }}
            >
              ✗ Verwerfen
            </button>
            <button
              className="primary"
              onClick={() => { onApplied(preview); onDismiss?.(); setAiPhase("idle"); setExpanded(false); }}
              style={{ fontSize: 11, padding: "2px 10px" }}
            >
              ✓ Übernehmen
            </button>
          </div>
        </div>
      )}
      {error && <span style={{ fontSize: 11, color: "var(--red)", marginTop: 4, display: "block" }}>{error}</span>}
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function QuestionItem({
  q,
  dismissed,
  docId,
  docContent,
  onToggleDismiss,
  onEdit,
  canEdit,
  onFixApplied,
  currentBody,
}: {
  q: AnalysisQuestion;
  dismissed: boolean;
  docId: string;
  docContent: string;
  onToggleDismiss: (id: string, value: boolean) => void;
  onEdit: (hint: string | null) => void;
  canEdit: boolean;
  onFixApplied?: (newBody: string) => void;
  currentBody?: string;
}) {
  const [fetchingHint, setFetchingHint] = useState(false);
  const [hintError, setHintError] = useState("");
  const notify = useNotify();

  async function handleRequestHint() {
    setFetchingHint(true);
    setHintError("");
    try {
      const { suggested_fix } = await api.fetchFixHint(docId, q.text, q.section, docContent);
      notify("✓ KI-Vorschlag erhalten", "success");
      onEdit(suggested_fix);
    } catch (e: unknown) {
      setHintError(e instanceof Error ? e.message : "Fehler beim Abrufen des Vorschlags.");
    } finally {
      setFetchingHint(false);
    }
  }

  return (
    <div style={{
      borderLeft: `3px solid ${SEVERITY_COLOR[q.severity]}`,
      paddingLeft: 10,
      marginBottom: 10,
      opacity: dismissed ? 0.45 : 1,
    }}>
      <div style={{ display: "flex", gap: 6, alignItems: "flex-start" }}>
        <span style={{ flexShrink: 0, fontSize: 13 }}>{SEVERITY_ICON[q.severity]}</span>
        <div style={{ flex: 1 }}>
          {q.section && (
            <span style={{ fontSize: 10, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, display: "block", marginBottom: 2 }}>
              {q.section}
            </span>
          )}
          <p style={{ fontSize: 13, lineHeight: 1.5, marginBottom: 6 }}>{q.text}</p>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
            <button
              onClick={() => onToggleDismiss(q.id, !dismissed)}
              style={{ fontSize: 11, padding: "2px 8px", color: dismissed ? "var(--green)" : "var(--muted)", borderColor: dismissed ? "var(--green)" : "var(--border)" }}
            >
              {dismissed ? "↩ Wiederherstellen" : "✓ Abhaken"}
            </button>
            {canEdit && !dismissed && (
              <>
                <button
                  onClick={() => onEdit(null)}
                  style={{ fontSize: 11, padding: "2px 8px", color: "var(--accent)", borderColor: "var(--accent)" }}
                >
                  ✏ Bearbeiten
                </button>
                <button
                  onClick={handleRequestHint}
                  disabled={fetchingHint}
                  style={{ fontSize: 11, padding: "2px 8px", color: "var(--yellow)", borderColor: "var(--yellow)" }}
                >
                  {fetchingHint ? "⏳ Lädt…" : "🤖 KI-Vorschlag"}
                </button>
              </>
            )}
            {onFixApplied && !dismissed && currentBody && (
              <FindingFixPanel
                findingText={q.text}
                findingSection={q.section}
                docId={docId}
                currentBody={currentBody}
                onApplied={onFixApplied}
                onDismiss={() => onToggleDismiss(q.id, true)}
              />
            )}
          </div>
          {hintError && (
            <p style={{ fontSize: 11, color: "var(--red)", marginTop: 4 }}>{hintError}</p>
          )}
        </div>
      </div>
    </div>
  );
}

function IssueItem({
  issue,
  onEdit,
  onFixApplied,
  docId,
  currentBody,
}: {
  issue: AnalysisIssue;
  onEdit: (hint: string | null) => void;
  onFixApplied?: (newBody: string) => void;
  docId?: string;
  currentBody?: string;
}) {
  return (
    <div style={{ borderLeft: `3px solid ${SEVERITY_COLOR[issue.severity]}`, paddingLeft: 10, marginBottom: 8 }}>
      <div style={{ display: "flex", gap: 6 }}>
        <span style={{ flexShrink: 0 }}>{SEVERITY_ICON[issue.severity]}</span>
        <div style={{ flex: 1 }}>
          {issue.section && (
            <span style={{ fontSize: 10, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, display: "block", marginBottom: 2 }}>
              {issue.section}
            </span>
          )}
          <p style={{ fontSize: 13, lineHeight: 1.5, marginBottom: 4 }}>{issue.text}</p>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
            <button
              onClick={() => onEdit(issue.suggested_fix ?? null)}
              style={{ fontSize: 11, padding: "2px 8px", color: "var(--accent)", borderColor: "var(--accent)" }}
            >
              ✏ Änderung bearbeiten
            </button>
            {onFixApplied && docId && currentBody && (
              <FindingFixPanel
                findingText={issue.text}
                findingSection={issue.section}
                docId={docId}
                currentBody={currentBody}
                onApplied={onFixApplied}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function SuggestionItem({
  s,
  onEdit,
  onFixApplied,
  docId,
  currentBody,
}: {
  s: { text: string; suggested_fix?: string | null };
  onEdit: (hint: string | null) => void;
  onFixApplied?: (newBody: string) => void;
  docId?: string;
  currentBody?: string;
}) {
  return (
    <div style={{ borderLeft: "3px solid var(--accent)", paddingLeft: 10, marginBottom: 8 }}>
      <p style={{ fontSize: 13, lineHeight: 1.5, marginBottom: 4 }}>💡 {s.text}</p>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <button
          onClick={() => onEdit(s.suggested_fix ?? null)}
          style={{ fontSize: 11, padding: "2px 8px", color: "var(--accent)", borderColor: "var(--accent)" }}
        >
          ✏ Änderung bearbeiten
        </button>
        {onFixApplied && docId && currentBody && (
          <FindingFixPanel
            findingText={s.text}
            docId={docId}
            currentBody={currentBody}
            onApplied={onFixApplied}
          />
        )}
      </div>
    </div>
  );
}

// ─── Body Editor ──────────────────────────────────────────────────────────────

function BodyEditor({
  docId,
  initialBody,
  fixHint,
  onSaved,
  onClose,
}: {
  docId: string;
  initialBody: string;
  fixHint: string | null;
  onSaved: () => void;
  onClose: () => void;
}) {
  const notify = useNotify();
  const [bodyText, setBodyText] = useState(initialBody);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      await api.patchContractBody(docId, bodyText);
      notify("✓ Contract gespeichert", "success");
      onSaved();
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler beim Speichern.");
    } finally {
      setSaving(false);
    }
  }

  function applyHint() {
    if (!fixHint) return;
    setBodyText(prev => prev + (prev.endsWith("\n") ? "" : "\n") + "\n" + fixHint);
  }

  return (
    <div style={{ marginTop: 16, borderTop: "1px solid var(--border)", paddingTop: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8 }}>
          Contract bearbeiten
        </span>
        <button onClick={onClose} style={{ fontSize: 12, padding: "2px 8px" }}>× Schließen</button>
      </div>

      {fixHint && (
        <div style={{ marginBottom: 10, background: "var(--surface)", border: "1px solid var(--accent)", borderRadius: 6, padding: 10 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
            <span style={{ fontSize: 11, color: "var(--accent)", textTransform: "uppercase", letterSpacing: 0.8 }}>
              KI-Vorschlag
            </span>
            <button
              onClick={applyHint}
              style={{ fontSize: 11, padding: "2px 8px", color: "var(--accent)", borderColor: "var(--accent)" }}
            >
              ↓ Ans Ende anfügen
            </button>
          </div>
          <pre style={{ fontSize: 12, whiteSpace: "pre-wrap", wordBreak: "break-word", margin: 0, color: "var(--fg)" }}>
            {fixHint}
          </pre>
        </div>
      )}

      <textarea
        value={bodyText}
        onChange={e => setBodyText(e.target.value)}
        rows={16}
        style={{
          width: "100%", fontFamily: "monospace", fontSize: 12,
          background: "var(--bg)", color: "var(--fg)", border: "1px solid var(--border)",
          borderRadius: 6, padding: 10, resize: "vertical", boxSizing: "border-box",
        }}
      />

      {error && <p style={{ color: "var(--red)", fontSize: 13, marginTop: 6 }}>{error}</p>}

      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button
          className="primary"
          onClick={handleSave}
          disabled={saving}
          style={{ fontSize: 12, padding: "5px 14px" }}
        >
          {saving ? "Speichert…" : "💾 In Contract schreiben"}
        </button>
        <button onClick={onClose} style={{ fontSize: 12, padding: "5px 14px" }}>
          Abbrechen
        </button>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function AnalyzePanel({ docId, docContent, docType, autoTrigger = false, onBodySaved, onSaveBody, forceStartKey }: Props) {
  const notify = useNotify();

  const [open, setOpen]         = useState(false);
  const [starting, setStarting] = useState(false);
  const [polling, setPolling]   = useState(false);
  const [error, setError]       = useState("");

  const [summaries, setSummaries]             = useState<AnalysisSummary[]>([]);
  const [selectedId, setSelectedId]           = useState<string | null>(null);
  const [current, setCurrent]                 = useState<PersistedAnalysis | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [showDismissed, setShowDismissed]     = useState(false);

  const [editFixHint, setEditFixHint] = useState<string | null>(null);
  const [editorOpen, setEditorOpen]   = useState(false);

  const [pendingBody, setPendingBody] = useState<string | null>(null);
  const [savingBody, setSavingBody]   = useState(false);

  const currentBody = pendingBody ?? docContent;

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const prevContentRef = useRef(docContent);

  useEffect(() => {
    if (!autoTrigger || !open || starting || polling) return;
    if (docContent === prevContentRef.current) return;
    prevContentRef.current = docContent;
    const timer = setTimeout(() => startAnalysis(), AUTO_TRIGGER_DELAY_MS);
    return () => clearTimeout(timer);
  }, [docContent, autoTrigger, open, starting, polling]);

  useEffect(() => {
    if (!open) return;
    api.listAnalyses(docId).then(list => {
      setSummaries(list);
      if (list.length > 0 && selectedId === null) {
        loadAnalysis(list[0].result_id);
      }
    }).catch(() => {});
  }, [open, docId]);

  useEffect(() => () => stopPoll(), []);

  const [pendingAutoStart, setPendingAutoStart] = useState(false);
  const prevForceKeyRef = useRef(0);
  useEffect(() => {
    if (!forceStartKey || forceStartKey === prevForceKeyRef.current) return;
    prevForceKeyRef.current = forceStartKey;
    setOpen(true);
    setPendingAutoStart(true);
  }, [forceStartKey]);
  useEffect(() => {
    if (!pendingAutoStart || !open || starting || polling) return;
    setPendingAutoStart(false);
    startAnalysis();
  }, [pendingAutoStart, open, starting, polling]);

  function stopPoll() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setPolling(false);
  }

  async function loadAnalysis(resultId: string) {
    setLoadingAnalysis(true);
    setSelectedId(resultId);
    try {
      const a = await api.getAnalysis(docId, resultId);
      setCurrent(a);
    } catch {
      setError("Analyse konnte nicht geladen werden.");
    } finally {
      setLoadingAnalysis(false);
    }
  }

  async function startAnalysis() {
    setStarting(true);
    setError("");
    try {
      const dismissedIds = current?.dismissed_ids ?? [];
      const { job_id } = await api.analyzeStart(docId, {
        content:       docContent,
        doc_type:      docType,
        dismissed_ids: dismissedIds,
      });
      setPolling(true);
      pollRef.current = setInterval(async () => {
        try {
          const status = await api.analyzeStatus(docId, job_id);
          if (status.status === "complete" && status.result_id) {
            stopPoll();
            notify(`✓ Analyse für ${docId} abgeschlossen`, "success");
            const [a, list] = await Promise.all([
              api.getAnalysis(docId, status.result_id),
              api.listAnalyses(docId),
            ]);
            setCurrent(a);
            setSummaries(list);
            setSelectedId(status.result_id);
          } else if (status.status === "failed") {
            stopPoll();
            setError(status.error ?? "Analyse fehlgeschlagen.");
            notify(`✕ Analyse fehlgeschlagen: ${status.error ?? ""}`, "error");
          }
        } catch {
          stopPoll();
          setError("Verbindung zum Server unterbrochen.");
        }
      }, POLL_INTERVAL_MS);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler beim Starten der Analyse.");
    } finally {
      setStarting(false);
    }
  }

  async function handleToggleDismiss(itemId: string, dismissed: boolean) {
    if (!current) return;
    try {
      const res = await api.dismissItem(docId, current.result_id, itemId, dismissed);
      setCurrent(prev => prev ? { ...prev, dismissed_ids: res.dismissed_ids } : prev);
      setSummaries(prev => prev.map(s =>
        s.result_id === current.result_id
          ? { ...s, dismissed_count: res.dismissed_ids.length }
          : s,
      ));
    } catch {
      setError("Fehler beim Speichern.");
    }
  }

  function handleEdit(hint: string | null) {
    setEditFixHint(hint);
    setEditorOpen(true);
  }

  function handleBodySaved() {
    setEditorOpen(false);
    setEditFixHint(null);
    onBodySaved?.();
  }

  async function handleSaveBody() {
    if (!pendingBody || !onSaveBody) return;
    setSavingBody(true);
    try {
      await onSaveBody(pendingBody);
      notify("✓ Spec aktualisiert", "success");
      setPendingBody(null);
    } catch (e) {
      notify(e instanceof Error ? e.message : "Fehler beim Speichern", "error");
    } finally {
      setSavingBody(false);
    }
  }

  const specFix = docType === "spec" && onSaveBody
    ? { onFixApplied: (nb: string) => setPendingBody(nb), currentBody }
    : {};

  // ─── Collapsed button ───────────────────────────────────────────────────────

  if (!open) {
    const pendingCount = current
      ? current.questions.filter(q => !current.dismissed_ids.includes(q.id)).length
      : 0;
    return (
      <button
        onClick={() => setOpen(true)}
        style={{ fontSize: 12, padding: "4px 12px", color: "var(--yellow)", borderColor: "var(--yellow)" }}
      >
        🔍 KI-Analyse
        {pendingCount > 0 && (
          <span style={{ marginLeft: 6, fontSize: 10, background: "var(--yellow)", color: "var(--bg)", borderRadius: 999, padding: "1px 5px" }}>
            {pendingCount}
          </span>
        )}
      </button>
    );
  }

  // ─── Expanded panel ─────────────────────────────────────────────────────────

  const dismissedIds       = current?.dismissed_ids ?? [];
  const activeQuestions    = current?.questions.filter(q => !dismissedIds.includes(q.id)) ?? [];
  const dismissedQuestions = current?.questions.filter(q => dismissedIds.includes(q.id)) ?? [];
  const isEmpty = current && activeQuestions.length === 0 && (current.issues?.length ?? 0) === 0 && (current.suggestions?.length ?? 0) === 0;
  const isRunning = polling || starting;
  const canEdit = docType === "contract";

  return (
    <section className="card" style={{ borderColor: "var(--yellow)" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <h3 style={{ fontSize: 12, color: "var(--yellow)", textTransform: "uppercase", letterSpacing: 1 }}>
          🔍 KI-Analyse
        </h3>
        <button onClick={() => { setOpen(false); stopPoll(); }} style={{ fontSize: 12, padding: "2px 8px" }}>×</button>
      </div>

      {/* Controls */}
      <div style={{ display: "flex", gap: 8, marginBottom: 14, alignItems: "center", flexWrap: "wrap" }}>
        <button
          className="primary"
          onClick={startAnalysis}
          disabled={isRunning}
          style={{ fontSize: 12, padding: "5px 14px", background: "var(--yellow)", borderColor: "var(--yellow)", color: "var(--bg)" }}
        >
          {starting ? "Startet…" : polling ? "⏳ Analysiert…" : current ? "Erneut analysieren" : "Analysieren"}
        </button>

        {summaries.length > 0 && (
          <select
            value={selectedId ?? ""}
            onChange={e => loadAnalysis(e.target.value)}
            style={{ fontSize: 11, padding: "3px 6px", background: "var(--surface)", color: "var(--fg)", border: "1px solid var(--border)", borderRadius: 4 }}
          >
            {summaries.map(s => (
              <option key={s.result_id} value={s.result_id}>
                {s.timestamp.replace("T", " ").slice(0, 16)}
                {" — "}
                {s.question_count}F {s.issue_count}P
                {s.dismissed_count > 0 ? ` (${s.dismissed_count}✓)` : ""}
              </option>
            ))}
          </select>
        )}

        {current && !isRunning && (
          <span style={{ fontSize: 11, color: "var(--muted)" }}>
            {activeQuestions.length > 0
              ? `${activeQuestions.length} offen`
              : "✓ Alle abgehakt"}
          </span>
        )}
      </div>

      {/* Pending body save bar */}
      {pendingBody && onSaveBody && (
        <div style={{
          display: "flex", gap: 8, alignItems: "center", marginBottom: 14,
          padding: "8px 10px", background: "var(--surface)",
          border: "1px solid var(--accent)", borderRadius: 6,
        }}>
          <span style={{ fontSize: 11, color: "var(--accent)", flex: 1 }}>
            ● Überarbeitungen ausstehend
          </span>
          <button
            onClick={() => setPendingBody(null)}
            style={{ fontSize: 11, padding: "2px 8px" }}
          >
            ↺ Verwerfen
          </button>
          <button
            className="primary"
            onClick={handleSaveBody}
            disabled={savingBody}
            style={{ fontSize: 11, padding: "3px 12px", background: "var(--accent)", borderColor: "var(--accent)", color: "#1e1e2e" }}
          >
            {savingBody ? "Speichert…" : "💾 In Spec schreiben"}
          </button>
        </div>
      )}

      {/* Error */}
      {error && <p style={{ color: "var(--red)", fontSize: 13, marginBottom: 10 }}>{error}</p>}

      {/* Loading state */}
      {polling && !current && (
        <p style={{ color: "var(--muted)", fontSize: 13 }}>Claude analysiert das Dokument…</p>
      )}
      {loadingAnalysis && (
        <p style={{ color: "var(--muted)", fontSize: 13 }}>Lade Analyse…</p>
      )}

      {/* Analysis result */}
      {!loadingAnalysis && current && (
        <div>
          {isEmpty && !isRunning && (
            <p style={{ color: "var(--green)", fontSize: 13 }}>✓ Dokument sieht vollständig aus.</p>
          )}

          {/* Active questions */}
          {activeQuestions.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              <p style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }}>
                Nachfragen
              </p>
              {activeQuestions.map(q => (
                <QuestionItem
                  key={q.id}
                  q={q}
                  dismissed={false}
                  docId={docId}
                  docContent={docContent}
                  onToggleDismiss={handleToggleDismiss}
                  onEdit={handleEdit}
                  canEdit={canEdit}
                  {...specFix}
                />
              ))}
            </div>
          )}

          {/* Issues */}
          {(current.issues?.length ?? 0) > 0 && (
            <div style={{ marginBottom: 14 }}>
              <p style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }}>
                Probleme
              </p>
              {current.issues.map((issue, i) => canEdit ? (
                <IssueItem
                  key={i}
                  issue={issue}
                  onEdit={handleEdit}
                  {...specFix}
                />
              ) : (
                <div key={i} style={{ borderLeft: `3px solid ${SEVERITY_COLOR[issue.severity]}`, paddingLeft: 10, marginBottom: 8 }}>
                  <div style={{ display: "flex", gap: 6 }}>
                    <span style={{ flexShrink: 0 }}>{SEVERITY_ICON[issue.severity]}</span>
                    <div style={{ flex: 1 }}>
                      {issue.section && (
                        <span style={{ fontSize: 10, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, display: "block", marginBottom: 2 }}>
                          {issue.section}
                        </span>
                      )}
                      <p style={{ fontSize: 13, lineHeight: 1.5, marginBottom: 4 }}>{issue.text}</p>
                      {specFix.onFixApplied && specFix.currentBody && (
                        <FindingFixPanel
                          findingText={issue.text}
                          findingSection={issue.section}
                          docId={docId}
                          currentBody={specFix.currentBody}
                          onApplied={specFix.onFixApplied}
                        />
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Suggestions */}
          {(current.suggestions?.length ?? 0) > 0 && (
            <div style={{ marginBottom: 14 }}>
              <p style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }}>
                Vorschläge
              </p>
              {current.suggestions.map((s, i) => canEdit ? (
                <SuggestionItem
                  key={i}
                  s={s}
                  onEdit={handleEdit}
                  {...specFix}
                />
              ) : (
                <div key={i} style={{ borderLeft: "3px solid var(--accent)", paddingLeft: 10, marginBottom: 8 }}>
                  <p style={{ fontSize: 13, lineHeight: 1.5, marginBottom: 4 }}>💡 {s.text}</p>
                  {specFix.onFixApplied && specFix.currentBody && (
                    <FindingFixPanel
                      findingText={s.text}
                      docId={docId}
                      currentBody={specFix.currentBody}
                      onApplied={specFix.onFixApplied}
                    />
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Dismissed section */}
          {dismissedQuestions.length > 0 && (
            <div style={{ marginTop: 12, paddingTop: 10, borderTop: "1px solid var(--border)" }}>
              <button
                onClick={() => setShowDismissed(v => !v)}
                style={{ fontSize: 11, color: "var(--muted)", background: "none", border: "none", cursor: "pointer", padding: 0 }}
              >
                {showDismissed ? "▾" : "▸"} {dismissedQuestions.length} erledigte Punkte
              </button>
              {showDismissed && (
                <div style={{ marginTop: 8 }}>
                  {dismissedQuestions.map(q => (
                    <QuestionItem
                      key={q.id}
                      q={q}
                      dismissed={true}
                      docId={docId}
                      docContent={docContent}
                      onToggleDismiss={handleToggleDismiss}
                      onEdit={handleEdit}
                      canEdit={canEdit}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Body Editor (contracts only) */}
          {canEdit && editorOpen && (
            <BodyEditor
              docId={docId}
              initialBody={docContent}
              fixHint={editFixHint}
              onSaved={handleBodySaved}
              onClose={() => { setEditorOpen(false); setEditFixHint(null); }}
            />
          )}
        </div>
      )}

      {/* No history yet */}
      {!loadingAnalysis && !current && !polling && !starting && summaries.length === 0 && (
        <p style={{ color: "var(--muted)", fontSize: 13 }}>Noch keine Analysen. Klicke „Analysieren" um zu starten.</p>
      )}
    </section>
  );
}
