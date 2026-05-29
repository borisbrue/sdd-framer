import { useEffect, useRef, useState } from "react";
import { api, AnalysisQuestion, AnalysisIssue, AnalysisSummary, PersistedAnalysis } from "../api";
import { useNotify } from "./NotificationContext";

const AUTO_TRIGGER_DELAY_MS = 3000;
const POLL_INTERVAL_MS = 2000;

interface Props {
  docId: string;
  docContent: string;
  docType: "spec" | "contract";
  autoTrigger?: boolean;
  onBodySaved?: () => void;
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

// ─── Sub-components ───────────────────────────────────────────────────────────

function QuestionItem({
  q,
  dismissed,
  docId,
  docContent,
  onToggleDismiss,
  onEdit,
  canEdit,
}: {
  q: AnalysisQuestion;
  dismissed: boolean;
  docId: string;
  docContent: string;
  onToggleDismiss: (id: string, value: boolean) => void;
  onEdit: (hint: string | null) => void;
  canEdit: boolean;
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
      const msg = e instanceof Error ? e.message : "Fehler beim Abrufen des Vorschlags.";
      setHintError(msg);
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
}: {
  issue: AnalysisIssue;
  onEdit: (hint: string | null) => void;
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
          <button
            onClick={() => onEdit(issue.suggested_fix ?? null)}
            style={{ fontSize: 11, padding: "2px 8px", color: "var(--accent)", borderColor: "var(--accent)" }}
          >
            ✏ Änderung bearbeiten
          </button>
        </div>
      </div>
    </div>
  );
}

function SuggestionItem({
  s,
  onEdit,
}: {
  s: { text: string; suggested_fix?: string | null };
  onEdit: (hint: string | null) => void;
}) {
  return (
    <div style={{ borderLeft: "3px solid var(--accent)", paddingLeft: 10, marginBottom: 8 }}>
      <p style={{ fontSize: 13, lineHeight: 1.5, marginBottom: 4 }}>💡 {s.text}</p>
      <button
        onClick={() => onEdit(s.suggested_fix ?? null)}
        style={{ fontSize: 11, padding: "2px 8px", color: "var(--accent)", borderColor: "var(--accent)" }}
      >
        ✏ Änderung bearbeiten
      </button>
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

export default function AnalyzePanel({ docId, docContent, docType, autoTrigger = false, onBodySaved, forceStartKey }: Props) {
  const notify = useNotify();

  const [open, setOpen]         = useState(false);
  const [starting, setStarting] = useState(false);
  const [polling, setPolling]   = useState(false);
  const [error, setError]       = useState("");

  // Verlauf
  const [summaries, setSummaries]         = useState<AnalysisSummary[]>([]);
  const [selectedId, setSelectedId]       = useState<string | null>(null);
  const [current, setCurrent]             = useState<PersistedAnalysis | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [showDismissed, setShowDismissed] = useState(false);

  // Body-Editor
  const [editFixHint, setEditFixHint] = useState<string | null>(null);
  const [editorOpen, setEditorOpen]   = useState(false);

  // Poll ref
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const prevContentRef = useRef(docContent);

  // Auto-trigger on content change
  useEffect(() => {
    if (!autoTrigger || !open || starting || polling) return;
    if (docContent === prevContentRef.current) return;
    prevContentRef.current = docContent;
    const timer = setTimeout(() => startAnalysis(), AUTO_TRIGGER_DELAY_MS);
    return () => clearTimeout(timer);
  }, [docContent, autoTrigger, open, starting, polling]);

  // Load summaries when panel opens
  useEffect(() => {
    if (!open) return;
    api.listAnalyses(docId).then(list => {
      setSummaries(list);
      if (list.length > 0 && selectedId === null) {
        loadAnalysis(list[0].result_id);
      }
    }).catch(() => {});
  }, [open, docId]);

  // Cleanup poll on unmount
  useEffect(() => () => stopPoll(), []);

  // Force-open + auto-start when triggered externally (z.B. nach Restrukturierung)
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

  const dismissedIds = current?.dismissed_ids ?? [];
  const activeQuestions  = current?.questions.filter(q => !dismissedIds.includes(q.id)) ?? [];
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

        {/* Verlauf-Selektor */}
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
              {current.issues.map((issue, i) => canEdit
                ? <IssueItem key={i} issue={issue} onEdit={handleEdit} />
                : (
                  <div key={i} style={{ borderLeft: `3px solid ${SEVERITY_COLOR[issue.severity]}`, paddingLeft: 10, marginBottom: 8 }}>
                    <div style={{ display: "flex", gap: 6 }}>
                      <span style={{ flexShrink: 0 }}>{SEVERITY_ICON[issue.severity]}</span>
                      <div>
                        {issue.section && (
                          <span style={{ fontSize: 10, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, display: "block", marginBottom: 2 }}>
                            {issue.section}
                          </span>
                        )}
                        <p style={{ fontSize: 13, lineHeight: 1.5 }}>{issue.text}</p>
                      </div>
                    </div>
                  </div>
                )
              )}
            </div>
          )}

          {/* Suggestions */}
          {(current.suggestions?.length ?? 0) > 0 && (
            <div style={{ marginBottom: 14 }}>
              <p style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }}>
                Vorschläge
              </p>
              {current.suggestions.map((s, i) => canEdit
                ? <SuggestionItem key={i} s={s} onEdit={handleEdit} />
                : (
                  <div key={i} style={{ borderLeft: "3px solid var(--accent)", paddingLeft: 10, marginBottom: 8 }}>
                    <span style={{ fontSize: 13 }}>💡 {s.text}</span>
                  </div>
                )
              )}
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

          {/* Body Editor */}
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
