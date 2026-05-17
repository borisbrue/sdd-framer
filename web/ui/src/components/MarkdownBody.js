import { jsx as _jsx } from "react/jsx-runtime";
import { useMemo } from "react";
import { marked } from "marked";
// IDs in Markdown-Text als klickbare Chips rendern
const ID_PATTERN = /\b(SPEC|CON|TST|ADR)-\d{4}\b/g;
export default function MarkdownBody({ markdown, onIdClick }) {
    const html = useMemo(() => marked.parse(markdown), [markdown]);
    if (!onIdClick) {
        return (_jsx("div", { className: "md-body", dangerouslySetInnerHTML: { __html: html } }));
    }
    // IDs im gerenderten HTML durch klickbare Spans ersetzen
    const enriched = html.replace(ID_PATTERN, (id) => `<span class="id-chip" data-id="${id}" title="Zur Detailansicht">${id}</span>`);
    return (_jsx("div", { className: "md-body", dangerouslySetInnerHTML: { __html: enriched }, onClick: (e) => {
            const el = e.target.closest("[data-id]");
            if (el?.dataset.id)
                onIdClick(el.dataset.id);
        } }));
}
