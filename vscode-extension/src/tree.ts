import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import { parseFrontmatter } from "./frontmatter";
import { PipelineRunState, TERMINAL_STATUSES } from "./pipeline";

export type NodeKind =
  | "spec"
  | "spec-approved"
  | "spec-running"
  | "spec-done-ok"
  | "spec-done-fail"
  | "contract"
  | "test"
  | "specsGroup"
  | "noProject";

export class SddNode extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly kind: NodeKind,
    public readonly filePath?: string,
    public readonly id_str?: string,
    collapsibleState = vscode.TreeItemCollapsibleState.None
  ) {
    super(label, collapsibleState);
    this.tooltip = filePath ? path.basename(filePath) : label;
    if (filePath) {
      this.resourceUri = vscode.Uri.file(filePath);
      this.command = {
        command: "vscode.open",
        title: "Öffnen",
        arguments: [vscode.Uri.file(filePath)],
      };
    }
    this.contextValue = kind;

    switch (kind) {
      case "specsGroup":
        this.iconPath = new vscode.ThemeIcon("folder");
        break;
      case "spec":
        this.iconPath = new vscode.ThemeIcon("file-text");
        break;
      case "spec-approved":
        this.iconPath = new vscode.ThemeIcon("play-circle");
        break;
      case "spec-running":
        this.iconPath = new vscode.ThemeIcon("sync~spin");
        break;
      case "spec-done-ok":
        this.iconPath = new vscode.ThemeIcon("pass", new vscode.ThemeColor("testing.iconPassed"));
        break;
      case "spec-done-fail":
        this.iconPath = new vscode.ThemeIcon("error", new vscode.ThemeColor("testing.iconFailed"));
        break;
      case "contract":
        this.iconPath = new vscode.ThemeIcon("verified");
        break;
      case "test":
        this.iconPath = new vscode.ThemeIcon("beaker");
        break;
      case "noProject":
        this.iconPath = new vscode.ThemeIcon("warning");
        break;
    }
  }
}

export class SddTreeProvider implements vscode.TreeDataProvider<SddNode> {
  private _onDidChangeTreeData = new vscode.EventEmitter<SddNode | undefined>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private _root: string | undefined;

  // specId → pipeline state (set by extension.ts during polling)
  private _pipelineRuns = new Map<string, PipelineRunState>();

  constructor(root?: string) {
    this._root = root;
  }

  setRoot(root: string): void {
    this._root = root;
    this._onDidChangeTreeData.fire(undefined);
  }

  refresh(): void {
    this._onDidChangeTreeData.fire(undefined);
  }

  setPipelineRun(specId: string, state: PipelineRunState): void {
    this._pipelineRuns.set(specId, state);
    this._onDidChangeTreeData.fire(undefined);
  }

  clearPipelineRun(specId: string): void {
    this._pipelineRuns.delete(specId);
    this._onDidChangeTreeData.fire(undefined);
  }

  getTreeItem(el: SddNode): vscode.TreeItem {
    return el;
  }

  getChildren(el?: SddNode): SddNode[] {
    if (!this._root) {
      if (!el) {
        return [new SddNode("Kein SDD-Projekt gefunden", "noProject")];
      }
      return [];
    }
    if (!el) {
      return this.buildRootNodes();
    }
    if (el.kind === "specsGroup") {
      return this.collectSpecs();
    }
    if (el.kind !== "noProject" && el.kind !== "contract" && el.kind !== "test" && el.filePath) {
      return this.childrenOfSpec(el.filePath);
    }
    return [];
  }

  private buildRootNodes(): SddNode[] {
    const specsDir = path.join(this._root!, ".sdd", "specs");
    let count = 0;
    try {
      count = fs.existsSync(specsDir)
        ? fs.readdirSync(specsDir).filter((f) => f.endsWith(".md") && f !== "README.md").length
        : 0;
    } catch {
      // ignore
    }
    return [
      new SddNode(
        `Specs (${count})`,
        "specsGroup",
        undefined,
        undefined,
        vscode.TreeItemCollapsibleState.Expanded
      ),
    ];
  }

  private collectSpecs(): SddNode[] {
    const specsDir = path.join(this._root!, ".sdd", "specs");
    if (!fs.existsSync(specsDir)) {
      return [];
    }
    try {
      return fs
        .readdirSync(specsDir)
        .filter((f: string) => f.endsWith(".md") && f !== "README.md")
        .sort()
        .map((f: string) => {
          const fp = path.join(specsDir, f);
          const fm = parseFrontmatter(fp);
          const specId = fm.id as string | undefined;
          const pipelineState = specId ? this._pipelineRuns.get(specId) : undefined;

          let kind: NodeKind = "spec";
          let description = fm.status ?? "";
          let tooltip = fp;

          if (pipelineState) {
            const attempts = Array.isArray(pipelineState.attempts) ? pipelineState.attempts.length : 0;
            const max = pipelineState.max_attempts ?? 3;
            if (pipelineState.status === "running") {
              kind = "spec-running";
              description = `${pipelineState.current_step} · Attempt ${attempts}/${max}`;
            } else if (pipelineState.status === "labeled" || pipelineState.status === "merged") {
              kind = "spec-done-ok";
              description = `✓ implementiert`;
              tooltip = pipelineState.report?.pr_url
                ? `PR: ${pipelineState.report.pr_url}`
                : "Pipeline erfolgreich";
            } else if (pipelineState.status === "failed") {
              kind = "spec-done-fail";
              description = `✗ fehlgeschlagen`;
              tooltip = pipelineState.report?.reason ?? "Pipeline fehlgeschlagen";
            } else if (pipelineState.status === "aborted") {
              kind = "spec-done-fail";
              description = `⊘ abgebrochen`;
            } else if (pipelineState.status === "dry_run") {
              kind = "spec-done-ok";
              description = `dry-run`;
            }
          } else if (fm.status === "approved") {
            kind = "spec-approved";
          }

          const label = specId ? `${specId}  ${fm.title ?? ""}` : f;
          const node = new SddNode(label, kind, fp, specId, vscode.TreeItemCollapsibleState.Collapsed);
          node.description = description;
          node.tooltip = tooltip;
          return node;
        });
    } catch {
      return [];
    }
  }

  private childrenOfSpec(specPath: string): SddNode[] {
    const fm = parseFrontmatter(specPath);
    const specId = fm.id as string | undefined;
    if (!specId) {
      return [];
    }

    const nodes: SddNode[] = [];

    for (const fp of this.collectMdFiles(path.join(this._root!, ".sdd", "contracts"))) {
      const cfm = parseFrontmatter(fp);
      if (cfm.spec === specId) {
        const cid = (cfm.id as string | undefined) ?? path.basename(fp);
        nodes.push(new SddNode(`${cid}  ${cfm.title ?? ""}`, "contract", fp, cid));
      }
    }

    for (const fp of this.collectMdFiles(path.join(this._root!, ".sdd", "tests"))) {
      const tfm = parseFrontmatter(fp);
      if (tfm.spec === specId) {
        const tid = (tfm.id as string | undefined) ?? path.basename(fp);
        nodes.push(new SddNode(`${tid}  ${tfm.title ?? ""}`, "test", fp, tid));
      }
    }

    return nodes;
  }

  private collectMdFiles(dir: string): string[] {
    if (!fs.existsSync(dir)) {
      return [];
    }
    const result: string[] = [];
    try {
      for (const e of fs.readdirSync(dir, { withFileTypes: true }) as fs.Dirent[]) {
        const full = path.join(dir, e.name);
        if (e.isDirectory()) {
          result.push(...this.collectMdFiles(full));
        } else if (e.name.endsWith(".md")) {
          result.push(full);
        }
      }
    } catch {
      // ignore
    }
    return result;
  }
}

// Utility: read all approved spec IDs from .sdd/specs/
export function collectApprovedSpecs(root: string): Array<{ id: string; title: string; filePath: string }> {
  const specsDir = path.join(root, ".sdd", "specs");
  if (!fs.existsSync(specsDir)) {
    return [];
  }
  try {
    return fs
      .readdirSync(specsDir)
      .filter((f: string) => f.endsWith(".md") && f !== "README.md")
      .flatMap((f: string) => {
        const fp = path.join(specsDir, f);
        const fm = parseFrontmatter(fp);
        if (fm.status === "approved" && fm.id) {
          return [{ id: fm.id as string, title: (fm.title as string) ?? "", filePath: fp }];
        }
        return [];
      });
  } catch {
    return [];
  }
}
