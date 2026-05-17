import { useMemo } from "react";
import { marked } from "marked";

interface Props {
  markdown: string;
  onIdClick?: (id: string) => void;
}

// IDs in Markdown-Text als klickbare Chips rendern
const ID_PATTERN = /\b(SPEC|CON|TST|ADR)-\d{4}\b/g;

export default function MarkdownBody({ markdown, onIdClick }: Props) {
  const html = useMemo(() => marked.parse(markdown) as string, [markdown]);

  if (!onIdClick) {
    return (
      <div
        className="md-body"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    );
  }

  // IDs im gerenderten HTML durch klickbare Spans ersetzen
  const enriched = html.replace(ID_PATTERN, (id) =>
    `<span class="id-chip" data-id="${id}" title="Zur Detailansicht">${id}</span>`
  );

  return (
    <div
      className="md-body"
      dangerouslySetInnerHTML={{ __html: enriched }}
      onClick={(e) => {
        const el = (e.target as HTMLElement).closest("[data-id]") as HTMLElement | null;
        if (el?.dataset.id) onIdClick(el.dataset.id);
      }}
    />
  );
}
