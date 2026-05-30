import { useEffect, useState } from "react";
import { Project } from "../config";
import { generateSpec, improveSpec, updateSpec, SddSpecDetail } from "../api";

const STEPS = [
  {
    title: "1. Kontext & Motivation",
    question: "Warum existiert dieses Feature? Welches Problem löst es?",
    placeholder: "Das bestehende System hat kein X, weshalb Y regelmäßig passiert...",
    sectionHint: "Kontext",
    aiInstruction: "Schreibe nur den Inhalt für Abschnitt '1. Kontext & Motivation'. Erkläre das Problem und warum dieses Feature gebraucht wird.",
  },
  {
    title: "2. Zielsetzung",
    question: "Was ist das Primärziel? Welche messbaren Erfolgskriterien gibt es? Was sind Nicht-Ziele?",
    placeholder: "**Primärziel:** ...\n\n**Erfolgskriterien:**\n- [ ] ...\n\n**Nicht-Ziele:**\n- ...",
    sectionHint: "Zielsetzung",
    aiInstruction: "Schreibe nur Abschnitt '2. Zielsetzung' mit Primärziel, messbaren Erfolgskriterien als Checkbox-Liste und expliziten Nicht-Zielen.",
  },
  {
    title: "3. User Stories",
    question: "Wer nutzt das Feature und wozu?",
    placeholder: "Als [Rolle] möchte ich [Fähigkeit], um [Nutzen].",
    sectionHint: "User Stories",
    aiInstruction: "Schreibe nur Abschnitt '3. User Stories' als Markdown-Tabelle (ID | Als ... | möchte ich ... | um ...).",
  },
  {
    title: "4. Akzeptanzkriterien",
    question: "Wann gilt dieses Feature als fertig? Beschreibe Happy Path und wichtige Szenarien.",
    placeholder: "```gherkin\nScenario: Happy Path\n  Given ...\n  When ...\n  Then ...\n```",
    sectionHint: "Akzeptanz",
    aiInstruction: "Schreibe nur Abschnitt '4. Akzeptanzkriterien' als Gherkin-Szenarien oder Checklist.",
  },
  {
    title: "5. Edge Cases & Fehler",
    question: "Was könnte schiefgehen? Welche Grenzfälle gibt es?",
    placeholder: "- Leere Eingabe: ...\n- Netzwerkfehler: ...\n- Ungültige Daten: ...",
    sectionHint: "Edge",
    aiInstruction: "Schreibe nur Abschnitt '5. Edge Cases & Fehlerfälle' als Bullet-Liste mit konkreten Szenarien.",
  },
] as const;

interface Props {
  project: Project;
  spec: SddSpecDetail;
  onSaved: (spec: SddSpecDetail) => void;
  onCancel: () => void;
}

export default function GuidedSpecEditor({ project, spec, onSaved, onCancel }: Props) {
  const [stepIndex, setStepIndex] = useState(0);
  const [answers, setAnswers] = useState<string[]>(STEPS.map(() => ""));
  const [aiLoading, setAiLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // On mount: generate full draft once and distribute to steps
  useEffect(() => {
    let active = true;
    setAiLoading(true);
    generateSpec(project, {
      title: spec.title,
      description: [
        "Erstelle einen vollständigen Spec-Body mit diesen Abschnitten:",
        "1. Kontext & Motivation",
        "2. Zielsetzung (Primärziel, messbare Erfolgskriterien als Checkbox-Liste, Nicht-Ziele)",
        "3. User Stories (Markdown-Tabelle)",
        "4. Akzeptanzkriterien (Gherkin oder Checklist)",
        "5. Edge Cases & Fehlerfälle (Bullet-Liste)",
      ].join("\n"),
    })
      .then(res => {
        if (!active) return;
        const sections = parseSections(res.result);
        setAnswers(STEPS.map((step) => {
          const match = Object.entries(sections).find(([k]) =>
            k.toLowerCase().includes(step.sectionHint.toLowerCase())
          );
          return match ? match[1] : "";
        }));
      })
      .catch(() => { /* user can request manually per step */ })
      .finally(() => { if (active) setAiLoading(false); });
    return () => { active = false; };
  }, [spec.id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleSuggest() {
    setAiLoading(true);
    setError("");
    try {
      const context = STEPS.slice(0, stepIndex)
        .map((s, i) => answers[i] ? `### ${s.title}\n${answers[i]}` : "")
        .filter(Boolean)
        .join("\n\n");

      const res = await improveSpec(
        project,
        spec.id,
        context || `Spec-Titel: ${spec.title}`,
        STEPS[stepIndex].aiInstruction,
      );
      setAnswers(prev => {
        const next = [...prev];
        next[stepIndex] = res.result;
        return next;
      });
    } catch {
      setError("Vorschlag konnte nicht generiert werden.");
    } finally {
      setAiLoading(false);
    }
  }

  async function handleFinish() {
    setSaving(true);
    setError("");
    try {
      const body = assembleBody(spec, answers);
      const updated = await updateSpec(project, spec.id, body);
      onSaved(updated);
    } catch {
      setError("Speichern fehlgeschlagen.");
      setSaving(false);
    }
  }

  const step = STEPS[stepIndex];
  const isLast = stepIndex === STEPS.length - 1;
  const progressPct = (stepIndex / STEPS.length) * 100;

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div style={{
        padding: "12px 16px",
        paddingTop: "calc(12px + env(safe-area-inset-top))",
        borderBottom: "1px solid var(--border)",
        background: "var(--surface)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
          <button onClick={onCancel} style={{ padding: "4px 10px", fontSize: 15 }}>←</button>
          <span style={{ flex: 1, fontWeight: 600, fontSize: 14, color: "var(--accent)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {spec.title}
          </span>
          <span style={{ fontSize: 12, color: "var(--muted)", flexShrink: 0 }}>
            {stepIndex + 1} / {STEPS.length}
          </span>
        </div>
        <div style={{ height: 3, background: "var(--border)", borderRadius: 2 }}>
          <div style={{
            height: "100%", width: `${progressPct}%`,
            background: "var(--accent)", borderRadius: 2,
            transition: "width 0.3s ease",
          }} />
        </div>
      </div>

      {/* Step content */}
      <div style={{ flex: 1, overflowY: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
        {/* Question card */}
        <div style={{
          background: "var(--surface)", borderRadius: 10, padding: 14,
          border: "1px solid var(--border)",
        }}>
          <div style={{ fontWeight: 700, fontSize: 13, color: "var(--accent)", marginBottom: 6, textTransform: "uppercase", letterSpacing: 0.5 }}>
            {step.title}
          </div>
          <div style={{ fontSize: 14, color: "var(--text)", lineHeight: 1.6 }}>
            {step.question}
          </div>
        </div>

        {/* Textarea with AI overlay */}
        <div style={{ position: "relative", flex: 1 }}>
          <textarea
            value={answers[stepIndex]}
            onChange={e => setAnswers(prev => {
              const next = [...prev];
              next[stepIndex] = e.target.value;
              return next;
            })}
            placeholder={step.placeholder}
            spellCheck={false}
            style={{
              width: "100%", minHeight: 200,
              padding: "12px",
              fontFamily: "monospace", fontSize: 16, lineHeight: 1.6,
              background: "var(--bg)", color: "var(--text)",
              border: "1px solid var(--border)", borderRadius: 8,
              resize: "vertical", boxSizing: "border-box", outline: "none",
            }}
          />
          {aiLoading && (
            <div style={{
              position: "absolute", inset: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              background: "rgba(29,32,33,0.75)", borderRadius: 8,
            }}>
              <span style={{ color: "var(--accent)", fontSize: 13 }}>KI generiert…</span>
            </div>
          )}
        </div>

        {/* AI suggest button */}
        <button
          onClick={handleSuggest}
          disabled={aiLoading}
          style={{ width: "100%", fontSize: 13, padding: "9px 0", color: "var(--accent)", borderColor: "var(--accent)" }}
        >
          {aiLoading ? "Generiere…" : "✦ KI-Vorschlag für diesen Schritt"}
        </button>

        {error && (
          <p style={{ color: "var(--red)", fontSize: 13, margin: 0, textAlign: "center" }}>{error}</p>
        )}
      </div>

      {/* Navigation footer */}
      <div style={{
        display: "flex", gap: 10, padding: "12px 16px",
        paddingBottom: "calc(12px + env(safe-area-inset-bottom))",
        borderTop: "1px solid var(--border)", background: "var(--surface)",
      }}>
        {stepIndex > 0 && (
          <button
            onClick={() => { setStepIndex(i => i - 1); setError(""); }}
            style={{ flex: 1, padding: "10px 0" }}
          >
            ← Zurück
          </button>
        )}
        {!isLast ? (
          <button
            className="primary"
            onClick={() => { setStepIndex(i => i + 1); setError(""); }}
            style={{ flex: 2, padding: "10px 0" }}
          >
            Weiter →
          </button>
        ) : (
          <button
            className="primary"
            onClick={handleFinish}
            disabled={saving}
            style={{ flex: 2, padding: "10px 0" }}
          >
            {saving ? "Speichern…" : "Spec speichern ✓"}
          </button>
        )}
      </div>
    </div>
  );
}

function parseSections(markdown: string): Record<string, string> {
  const sections: Record<string, string> = {};
  const lines = markdown.split("\n");
  let currentKey = "";
  let currentLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("## ")) {
      if (currentKey) sections[currentKey] = currentLines.join("\n").trim();
      currentKey = line.slice(3).trim();
      currentLines = [];
    } else {
      currentLines.push(line);
    }
  }
  if (currentKey) sections[currentKey] = currentLines.join("\n").trim();
  return sections;
}

function assembleBody(spec: SddSpecDetail, answers: string[]): string {
  const today = new Date().toISOString().slice(0, 10);
  const lines: string[] = [
    `# ${spec.title}`,
    ``,
    `> **Status:** ${spec.status} · **Owner:** ${spec.owner || "Boris"} · **Version:** 0.1.0`,
    ``,
  ];
  STEPS.forEach((step, i) => {
    lines.push(`## ${step.title}`);
    lines.push("");
    lines.push(answers[i] || `<!-- ${step.placeholder} -->`);
    lines.push("");
  });
  lines.push(`## 6. Änderungshistorie`);
  lines.push("");
  lines.push(`| Datum      | Version | Autor          | Änderung            |`);
  lines.push(`|------------|---------|----------------|---------------------|`);
  lines.push(`| ${today} | 0.1.0   | ${spec.owner || "Boris"} | Initiale Erstellung |`);
  return lines.join("\n");
}
