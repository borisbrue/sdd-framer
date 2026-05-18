"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.SddTreeProvider = exports.SddNode = void 0;
exports.collectApprovedSpecs = collectApprovedSpecs;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const frontmatter_1 = require("./frontmatter");
class SddNode extends vscode.TreeItem {
    constructor(label, kind, filePath, id_str, collapsibleState = vscode.TreeItemCollapsibleState.None) {
        super(label, collapsibleState);
        this.label = label;
        this.kind = kind;
        this.filePath = filePath;
        this.id_str = id_str;
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
exports.SddNode = SddNode;
class SddTreeProvider {
    constructor(root) {
        this._onDidChangeTreeData = new vscode.EventEmitter();
        this.onDidChangeTreeData = this._onDidChangeTreeData.event;
        // specId → pipeline state (set by extension.ts during polling)
        this._pipelineRuns = new Map();
        this._root = root;
    }
    setRoot(root) {
        this._root = root;
        this._onDidChangeTreeData.fire(undefined);
    }
    refresh() {
        this._onDidChangeTreeData.fire(undefined);
    }
    setPipelineRun(specId, state) {
        this._pipelineRuns.set(specId, state);
        this._onDidChangeTreeData.fire(undefined);
    }
    clearPipelineRun(specId) {
        this._pipelineRuns.delete(specId);
        this._onDidChangeTreeData.fire(undefined);
    }
    getTreeItem(el) {
        return el;
    }
    getChildren(el) {
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
    buildRootNodes() {
        const specsDir = path.join(this._root, ".sdd", "specs");
        let count = 0;
        try {
            count = fs.existsSync(specsDir)
                ? fs.readdirSync(specsDir).filter((f) => f.endsWith(".md") && f !== "README.md").length
                : 0;
        }
        catch {
            // ignore
        }
        return [
            new SddNode(`Specs (${count})`, "specsGroup", undefined, undefined, vscode.TreeItemCollapsibleState.Expanded),
        ];
    }
    collectSpecs() {
        const specsDir = path.join(this._root, ".sdd", "specs");
        if (!fs.existsSync(specsDir)) {
            return [];
        }
        try {
            return fs
                .readdirSync(specsDir)
                .filter((f) => f.endsWith(".md") && f !== "README.md")
                .sort()
                .map((f) => {
                const fp = path.join(specsDir, f);
                const fm = (0, frontmatter_1.parseFrontmatter)(fp);
                const specId = fm.id;
                const pipelineState = specId ? this._pipelineRuns.get(specId) : undefined;
                let kind = "spec";
                let description = fm.status ?? "";
                let tooltip = fp;
                if (pipelineState) {
                    const attempts = Array.isArray(pipelineState.attempts) ? pipelineState.attempts.length : 0;
                    const max = pipelineState.max_attempts ?? 3;
                    if (pipelineState.status === "running") {
                        kind = "spec-running";
                        description = `${pipelineState.current_step} · Attempt ${attempts}/${max}`;
                    }
                    else if (pipelineState.status === "labeled" || pipelineState.status === "merged") {
                        kind = "spec-done-ok";
                        description = `✓ implementiert`;
                        tooltip = pipelineState.report?.pr_url
                            ? `PR: ${pipelineState.report.pr_url}`
                            : "Pipeline erfolgreich";
                    }
                    else if (pipelineState.status === "failed") {
                        kind = "spec-done-fail";
                        description = `✗ fehlgeschlagen`;
                        tooltip = pipelineState.report?.reason ?? "Pipeline fehlgeschlagen";
                    }
                    else if (pipelineState.status === "aborted") {
                        kind = "spec-done-fail";
                        description = `⊘ abgebrochen`;
                    }
                    else if (pipelineState.status === "dry_run") {
                        kind = "spec-done-ok";
                        description = `dry-run`;
                    }
                }
                else if (fm.status === "approved") {
                    kind = "spec-approved";
                }
                const label = specId ? `${specId}  ${fm.title ?? ""}` : f;
                const node = new SddNode(label, kind, fp, specId, vscode.TreeItemCollapsibleState.Collapsed);
                node.description = description;
                node.tooltip = tooltip;
                return node;
            });
        }
        catch {
            return [];
        }
    }
    childrenOfSpec(specPath) {
        const fm = (0, frontmatter_1.parseFrontmatter)(specPath);
        const specId = fm.id;
        if (!specId) {
            return [];
        }
        const nodes = [];
        for (const fp of this.collectMdFiles(path.join(this._root, ".sdd", "contracts"))) {
            const cfm = (0, frontmatter_1.parseFrontmatter)(fp);
            if (cfm.spec === specId) {
                const cid = cfm.id ?? path.basename(fp);
                nodes.push(new SddNode(`${cid}  ${cfm.title ?? ""}`, "contract", fp, cid));
            }
        }
        for (const fp of this.collectMdFiles(path.join(this._root, ".sdd", "tests"))) {
            const tfm = (0, frontmatter_1.parseFrontmatter)(fp);
            if (tfm.spec === specId) {
                const tid = tfm.id ?? path.basename(fp);
                nodes.push(new SddNode(`${tid}  ${tfm.title ?? ""}`, "test", fp, tid));
            }
        }
        return nodes;
    }
    collectMdFiles(dir) {
        if (!fs.existsSync(dir)) {
            return [];
        }
        const result = [];
        try {
            for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
                const full = path.join(dir, e.name);
                if (e.isDirectory()) {
                    result.push(...this.collectMdFiles(full));
                }
                else if (e.name.endsWith(".md")) {
                    result.push(full);
                }
            }
        }
        catch {
            // ignore
        }
        return result;
    }
}
exports.SddTreeProvider = SddTreeProvider;
// Utility: read all approved spec IDs from .sdd/specs/
function collectApprovedSpecs(root) {
    const specsDir = path.join(root, ".sdd", "specs");
    if (!fs.existsSync(specsDir)) {
        return [];
    }
    try {
        return fs
            .readdirSync(specsDir)
            .filter((f) => f.endsWith(".md") && f !== "README.md")
            .flatMap((f) => {
            const fp = path.join(specsDir, f);
            const fm = (0, frontmatter_1.parseFrontmatter)(fp);
            if (fm.status === "approved" && fm.id) {
                return [{ id: fm.id, title: fm.title ?? "", filePath: fp }];
            }
            return [];
        });
    }
    catch {
        return [];
    }
}
//# sourceMappingURL=tree.js.map