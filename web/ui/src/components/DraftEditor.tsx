import { useMemo, useState } from "react";
import { api } from "../api";
import { useNotify } from "./NotificationContext";
import SectionBlock from "./SectionBlock";

function extractToc(body: string): string {
  return body.split("\n").filter(l => /^#{1,3} /.test(l)).join("\n");
}

// ── Section parsing ────────────────────────────────────────────────────────────

interface Section {
  key: string;
  heading: string;
  content: string;
}

function parseSections(body: string): Section[] {
  const lines = body.split("\n");
  // Remove the trailing empty string produced by a terminal \n
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

  const filtered = sections.filter((s, i) => i > 0 || s.heading || s.content.trim());
  return filtered.length > 0 ? filtered : [{ key: "empty", heading: "", content: "" }];
}

function sectionsToBody(sections: Section[]): string {
  return sections
    .map(s => (s.heading ? s.heading + "\n" + s.content : s.content))
    .join("");
}

// ── Component ──────────────────────────────────────────────────────────────────

interface Props {
  specId: string;
  initialBody: string;
  dependsOn: string[];
  onSaved: (newBody: string) => void;
  onNavigate: (id: string) => void;
}

export default function DraftEditor({ specId, initialBody, dependsOn, onSaved, onNavigate }: Props) {
  const notify = useNotify();
  const [sections, setSections]           = useState<Section[]>(() => parseSections(initialBody));
  const [initialSections]                 = useState<Section[]>(() => parseSections(initialBody));
  const [saving, setSaving]               = useState(false);

  const currentBody = useMemo(() => sectionsToBody(sections), [sections]);
  const specToc = useMemo(() => extractToc(currentBody), [currentBody]);

  const linkedSpecIds = useMemo(() => {
    const inline = [...currentBody.matchAll(/\bSPEC-\d{4}\b/g)].map(m => m[0]);
    return [...new Set([...dependsOn, ...inline])].filter(id => id !== specId);
  }, [currentBody, dependsOn, specId]);

  const hasAnyDirty = sections.some((s, i) => s.content !== (initialSections[i]?.content ?? ""));

  const updateSection = (index: number, newContent: string) => {
    setSections(prev => prev.map((s, i) => i === index ? { ...s, content: newContent } : s));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.updateSpec(specId, currentBody);
      notify("✓ Spec gespeichert", "success");
      onSaved(currentBody);
    } catch (e) {
      notify(e instanceof Error ? e.message : "Fehler beim Speichern", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {/* Header */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        marginBottom: 10,
      }}>
        <span style={{ fontSize: 12, color: "var(--accent)", textTransform: "uppercase", letterSpacing: 1, fontWeight: 600 }}>
          ✦ Draft-Editor
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {linkedSpecIds.length > 0 && (
            <span style={{ fontSize: 10, color: "var(--muted)" }}>
              Kontext: {linkedSpecIds.length} verlinkte Spec{linkedSpecIds.length > 1 ? "s" : ""}
            </span>
          )}
          <button
            className="primary"
            onClick={handleSave}
            disabled={saving || !hasAnyDirty}
            style={{ fontSize: 11, padding: "3px 12px", opacity: hasAnyDirty ? 1 : 0.4 }}
          >
            {saving ? "Speichert…" : "💾 Alle speichern"}
          </button>
        </div>
      </div>

      {/* Section blocks */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {sections.map((section, i) => (
          <SectionBlock
            key={section.key}
            heading={section.heading}
            content={section.content}
            index={i}
            specId={specId}
            linkedSpecIds={linkedSpecIds}
            fullSpecContent={specToc}
            isDirty={section.content !== (initialSections[i]?.content ?? "")}
            onContentChange={updateSection}
            onNavigate={onNavigate}
          />
        ))}
      </div>
    </div>
  );
}
