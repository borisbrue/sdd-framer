import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";

const ID_RE = /\b(SPEC|CON|TST|ADR)-\d{4}\b/g;

function findFileById(id: string, rootDirs: string[]): string | undefined {
  const prefix = id.split("-")[0];
  const subdirs: Record<string, string[]> = {
    SPEC: ["specs"],
    CON:  ["contracts", "contracts/api", "contracts/behavior", "contracts/data", "contracts/performance"],
    TST:  ["tests", "tests/unit", "tests/contract", "tests/acceptance", "tests/performance", "tests/property"],
    ADR:  ["docs/adr"],
  };
  const searchDirs = subdirs[prefix] ?? [];

  for (const root of rootDirs) {
    for (const sub of searchDirs) {
      const dir = path.join(root, sub);
      if (!fs.existsSync(dir)) {
        continue;
      }
      const match = fs.readdirSync(dir).find(
        (f) => f.startsWith(id) && f.endsWith(".md")
      );
      if (match) {
        return path.join(dir, match);
      }
    }
  }
  return undefined;
}

export class SddDefinitionProvider implements vscode.DefinitionProvider {
  constructor(private projectRoot: string) {}

  provideDefinition(
    document: vscode.TextDocument,
    position: vscode.Position
  ): vscode.Definition | undefined {
    const line = document.lineAt(position.line).text;
    let match: RegExpExecArray | null;
    ID_RE.lastIndex = 0;

    while ((match = ID_RE.exec(line)) !== null) {
      const start = match.index;
      const end = start + match[0].length;
      if (position.character >= start && position.character <= end) {
        const id = match[0];
        const filePath = findFileById(id, [this.projectRoot]);
        if (filePath) {
          return new vscode.Location(
            vscode.Uri.file(filePath),
            new vscode.Position(0, 0)
          );
        }
      }
    }
    return undefined;
  }
}

export class SddHoverProvider implements vscode.HoverProvider {
  constructor(private projectRoot: string) {}

  provideHover(
    document: vscode.TextDocument,
    position: vscode.Position
  ): vscode.Hover | undefined {
    const line = document.lineAt(position.line).text;
    let match: RegExpExecArray | null;
    ID_RE.lastIndex = 0;

    while ((match = ID_RE.exec(line)) !== null) {
      const start = match.index;
      const end = start + match[0].length;
      if (position.character >= start && position.character <= end) {
        const id = match[0];
        const filePath = findFileById(id, [this.projectRoot]);
        if (filePath) {
          try {
            const text = fs.readFileSync(filePath, "utf8");
            const titleMatch = /^title:\s*"?(.+?)"?\s*$/m.exec(text);
            const statusMatch = /^status:\s*(\S+)/m.exec(text);
            const title = titleMatch ? titleMatch[1] : "(kein Titel)";
            const status = statusMatch ? statusMatch[1] : "?";
            return new vscode.Hover(
              new vscode.MarkdownString(`**${id}** – ${title}\n\nStatus: \`${status}\``)
            );
          } catch {
            return undefined;
          }
        }
      }
    }
    return undefined;
  }
}

