import * as vscode from "vscode";
import { runSdd } from "./cli";

const COLLECTION_NAME = "sdd";

export function createDiagnosticCollection(): vscode.DiagnosticCollection {
  return vscode.languages.createDiagnosticCollection(COLLECTION_NAME);
}

interface SddIssue {
  severity: "error" | "warning";
  file: string;
  message: string;
  instruction?: string;
}

export async function runValidation(
  projectRoot: string,
  collection: vscode.DiagnosticCollection
): Promise<void> {
  collection.clear();

  let issues: SddIssue[] = [];
  try {
    const result = await runSdd(["validate", "--instruct"], projectRoot);
    const parsed = JSON.parse(result.stdout) as { issues: SddIssue[] };
    issues = parsed.issues ?? [];
  } catch {
    return;
  }

  const byFile = new Map<string, vscode.Diagnostic[]>();

  for (const issue of issues) {
    const absPath = vscode.Uri.file(`${projectRoot}/${issue.file}`);
    const severity =
      issue.severity === "error"
        ? vscode.DiagnosticSeverity.Error
        : vscode.DiagnosticSeverity.Warning;

    const message = issue.instruction
      ? `${issue.message}\n→ ${issue.instruction}`
      : issue.message;

    const diag = new vscode.Diagnostic(
      new vscode.Range(0, 0, 0, 0),
      message,
      severity
    );
    diag.source = "sdd";

    const key = absPath.toString();
    if (!byFile.has(key)) {
      byFile.set(key, []);
    }
    byFile.get(key)!.push(diag);
  }

  for (const [uri, diags] of byFile) {
    collection.set(vscode.Uri.parse(uri), diags);
  }
}
