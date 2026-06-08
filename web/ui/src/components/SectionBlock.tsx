import { useEffect, useState } from "react";
import { api, AiUsageEntry } from "../api";
import MarkdownBody from "./MarkdownBody";

export interface SectionBlockProps {
  heading: string;
  content: string;
  index: number;
  specId: string;
  linkedSpecIds: string[];
  fullSpecContent: string;
  isDirty: boolean;
  onContentChange: (index: number, newContent: string) => void;
  onNavigate: (id: string) => void;
}

function UsagePill({ entry }: { entry: AiUsageEntry }) {
  const isCli = entry.provider === "claude-cli";
  return (
    <span style={{ fontSize: 10, color: "var(--muted)", fontFamily: "monospace" }}>
      {isCli
        ? "claude-cli"
        : `${entry.input_tokens}↑ ${entry.output_tokens}↓ $${(entry.cost_usd ?? 0).toFixed(5)}`}
    </span>
  );
}

export default function SectionBlock({
  heading, content, index, specId, linkedSpecIds, fullSpecContent,
  isDirty, onContentChange, onNavigate,
}: SectionBlockProps) {
  const [isEditing, setIsEditing]     = useState(false);
  const [localContent, setLocalContent] = useState(content);
  const [instruction, setInstruction] = useState("");
  const [aiPhase, setAiPhase]         = useState<"idle" | "generating" | "preview">("idle");
  const [preview, setPreview]         = useState("");
  const [usage, setUsage]             = useState<AiUsageEntry | null>(null);
  const [error, setError]             = useState("");

  useEffect(() => { setLocalContent(content); }, [content]);

  const stopEditing = () => {
    setIsEditing(false);
    onContentChange(index, localContent);
  };

  const handleGenerate = async () => {
    if (!instruction.trim() || aiPhase !== "idle") return;
    setAiPhase("generating");
    setError("");
    try {
      const res = await api.aiImproveSection({
        spec_id: specId,
        section_heading: heading,
        section_content: localContent,
        instructions: instruction,
        full_spec_content: fullSpecContent,
        linked_spec_ids: linkedSpecIds,
      });
      setPreview(res.result);
      setUsage(res.usage);
      setAiPhase("preview");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler beim Generieren.");
      setAiPhase("idle");
    }
  };

  const handleAccept = () => {
    const trimmed = preview.trimEnd() + "\n";
    setLocalContent(trimmed);
    onContentChange(index, trimmed);
    setAiPhase("idle");
    setPreview("");
    setInstruction("");
    setUsage(null);
  };

  const handleDiscard = () => {
    setAiPhase("idle");
    setPreview("");
    setUsage(null);
  };

  const headingText = heading.replace(/^#{1,3}\s+/, "");
  const headingLevel = (heading.match(/^(#{1,3})/)?.[1].length ?? 0) as 0 | 1 | 2 | 3;
  const fontSize = headingLevel === 1 ? 16 : headingLevel === 2 ? 14 : 13;

  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>

      {/* ── Heading bar ── */}
      {heading && (
        <div style={{
          padding: "7px 14px", background: "var(--surface)",
          borderBottom: "1px solid var(--border)",
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <span style={{ fontSize, fontWeight: 700, color: "var(--text)" }}>{headingText}</span>
          {isDirty && <span style={{ fontSize: 10, color: "var(--accent)" }}>● bearbeitet</span>}
        </div>
      )}

      {/* ── Content area ── */}
      <div style={{ padding: "10px 14px" }}>
        {isEditing ? (
          <textarea
            autoFocus
            value={localContent}
            onChange={e => setLocalContent(e.target.value)}
            onBlur={stopEditing}
            onKeyDown={e => { if (e.key === "Escape") { e.currentTarget.blur(); } }}
            rows={Math.max(3, localContent.split("\n").length + 1)}
            style={{
              width: "100%", fontFamily: "monospace", fontSize: 12,
              background: "var(--bg)", color: "var(--text)",
              border: "1px solid var(--accent)", borderRadius: 4,
              padding: 8, resize: "vertical", boxSizing: "border-box", display: "block",
            }}
          />
        ) : aiPhase === "preview" ? (
          <div>
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontSize: 10, color: "var(--accent)", textTransform: "uppercase", letterSpacing: 0.8 }}>
                ✦ KI-Vorschlag
              </span>
              <div style={{
                marginTop: 6, padding: "8px 12px", borderRadius: 4,
                background: "var(--bg)", border: "1px solid var(--accent)",
              }}>
                <MarkdownBody markdown={preview} onIdClick={onNavigate} />
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              {usage && <UsagePill entry={usage} />}
              <button onClick={handleDiscard} style={{ fontSize: 11, padding: "2px 8px" }}>
                ✗ Verwerfen
              </button>
              <button className="primary" onClick={handleAccept} style={{ fontSize: 11, padding: "2px 10px" }}>
                ✓ Übernehmen
              </button>
            </div>
          </div>
        ) : (
          <div
            onClick={() => setIsEditing(true)}
            style={{ cursor: "text", minHeight: 28 }}
            title="Klicken zum Bearbeiten"
          >
            {localContent.trim() ? (
              <MarkdownBody markdown={localContent} onIdClick={onNavigate} />
            ) : (
              <span style={{ color: "var(--muted)", fontSize: 12, fontStyle: "italic" }}>
                Hier klicken um Text hinzuzufügen…
              </span>
            )}
          </div>
        )}
      </div>

      {/* ── AI instruction bar ── */}
      {aiPhase !== "preview" && (
        <div style={{
          padding: "6px 14px", borderTop: "1px solid var(--border)",
          background: "var(--bg)", display: "flex", gap: 8, alignItems: "center",
        }}>
          <input
            value={instruction}
            onChange={e => setInstruction(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); handleGenerate(); } }}
            placeholder={`✦ Anweisung für „${headingText || "diesen Abschnitt"}"…`}
            disabled={aiPhase === "generating"}
            style={{
              flex: 1, fontSize: 12, padding: "4px 8px",
              background: "var(--surface)", color: "var(--text)",
              border: "1px solid var(--border)", borderRadius: 4,
              opacity: aiPhase === "generating" ? 0.6 : 1,
            }}
          />
          <button
            onClick={handleGenerate}
            disabled={!instruction.trim() || aiPhase === "generating"}
            style={{
              fontSize: 12, padding: "4px 12px", whiteSpace: "nowrap",
              background: "var(--accent)", color: "#1e1e2e",
              border: "none", borderRadius: 4, cursor: "pointer",
              opacity: (!instruction.trim() || aiPhase === "generating") ? 0.5 : 1,
            }}
          >
            {aiPhase === "generating" ? "✦ …" : "✦"}
          </button>
          {error && <span style={{ fontSize: 11, color: "var(--red)" }}>{error}</span>}
        </div>
      )}
    </div>
  );
}
