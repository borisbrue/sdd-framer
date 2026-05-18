import { useMemo } from "react";
import { marked } from "marked";

marked.setOptions({ gfm: true, breaks: false });

interface Props {
  content: string;
}

export default function MarkdownBody({ content }: Props) {
  const html = useMemo(() => {
    const result = marked.parse(content);
    return typeof result === "string" ? result : "";
  }, [content]);

  return (
    <div
      className="md-body"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
