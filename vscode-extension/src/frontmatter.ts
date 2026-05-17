import * as fs from "fs";

export interface Frontmatter {
  id?: string;
  title?: string;
  status?: string;
  contracts?: string[];
  tests?: string[];
  spec?: string;
  contract?: string;
  level?: string;
  type?: string;
  [key: string]: unknown;
}

const FM_RE = /^---\s*\n([\s\S]*?)\n---\s*\n/;

export function parseFrontmatter(filePath: string): Frontmatter {
  try {
    const text = fs.readFileSync(filePath, "utf8");
    const m = FM_RE.exec(text);
    if (!m) {
      return {};
    }
    // Minimaler YAML-Parser für flache Key-Value-Paare und Listen
    return parseYamlLite(m[1]);
  } catch {
    return {};
  }
}

function parseYamlLite(yaml: string): Frontmatter {
  const result: Frontmatter = {};
  const lines = yaml.split("\n");
  let currentKey: string | null = null;
  let inList = false;

  for (const raw of lines) {
    const line = raw.replace(/#.*$/, "").trimEnd(); // Kommentare entfernen

    // Listenelement
    const listMatch = /^(\s+)-\s+(.+)$/.exec(line);
    if (listMatch && inList && currentKey) {
      const val = listMatch[2].trim().replace(/^["']|["']$/g, "");
      (result[currentKey] as string[]).push(val);
      continue;
    }

    // Key: Value
    const kvMatch = /^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$/.exec(line);
    if (kvMatch) {
      currentKey = kvMatch[1];
      const raw_val = kvMatch[2].trim();
      if (raw_val === "" || raw_val === "[]") {
        result[currentKey] = raw_val === "[]" ? [] : undefined;
        inList = raw_val === "";
      } else if (raw_val.startsWith("[")) {
        // Inline-Liste: [CON-0001, CON-0002]
        result[currentKey] = raw_val
          .replace(/^\[|\]$/g, "")
          .split(",")
          .map((s) => s.trim().replace(/^["']|["']$/g, ""))
          .filter(Boolean);
        inList = false;
      } else {
        result[currentKey] = raw_val.replace(/^["']|["']$/g, "");
        inList = false;
      }
    }
  }
  return result;
}
