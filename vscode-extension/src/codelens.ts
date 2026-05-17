import * as vscode from "vscode";
import { parseFrontmatter } from "./frontmatter";

export class SddCodeLensProvider implements vscode.CodeLensProvider {
  provideCodeLenses(document: vscode.TextDocument): vscode.CodeLens[] {
    const fm = parseFrontmatter(document.fileName);
    if (!fm.id || !fm.id.startsWith("SPEC-")) {
      return [];
    }

    const contracts = fm.contracts?.length ?? 0;
    const tests = fm.tests?.length ?? 0;
    const issues = (contracts === 0 ? 1 : 0) + (tests === 0 ? 1 : 0);
    const issueLabel = issues > 0 ? ` · ⚠ ${issues} Lücken` : " · ✓";

    const lens = new vscode.CodeLens(new vscode.Range(0, 0, 0, 0), {
      title: `${contracts} contracts · ${tests} tests${issueLabel}`,
      command: "sdd.validate",
    });
    return [lens];
  }
}
