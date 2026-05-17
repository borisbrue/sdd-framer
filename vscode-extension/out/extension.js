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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const cli_1 = require("./cli");
const tree_1 = require("./tree");
const diagnostics_1 = require("./diagnostics");
const codelens_1 = require("./codelens");
const definition_1 = require("./definition");
const analyzeView_1 = require("./analyzeView");
const server_1 = require("./server");
const pipeline_1 = require("./pipeline");
const frontmatter_1 = require("./frontmatter");
const out = vscode.window.createOutputChannel("SDD Framer");
async function activate(context) {
    out.appendLine("SDD Framer aktiviert.");
    const server = server_1.ServerManager.getInstance(out);
    const pipelineClient = new pipeline_1.PipelineClient(() => {
        return server.getBaseUrl() ?? vscode.workspace.getConfiguration("sdd").get("webApiUrl", "http://localhost:8000");
    });
    // Status Bar
    const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    updateStatusBar(statusBar, server);
    server.onDidChangeStatus(() => updateStatusBar(statusBar, server), undefined, context.subscriptions);
    statusBar.show();
    context.subscriptions.push(statusBar);
    // TreeView
    const treeProvider = new tree_1.SddTreeProvider();
    context.subscriptions.push(vscode.window.registerTreeDataProvider("sddTree", treeProvider), out);
    // Analyze-Panel
    const analyzeProvider = new analyzeView_1.SddAnalyzeViewProvider(context);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider(analyzeView_1.SddAnalyzeViewProvider.viewId, analyzeProvider));
    // Diagnostics
    const diagCollection = (0, diagnostics_1.createDiagnosticCollection)();
    context.subscriptions.push(diagCollection);
    let root = "";
    // ── Commands ─────────────────────────────────────────────────────────────
    context.subscriptions.push(
    // Existing
    vscode.commands.registerCommand("sdd.analyzeDoc", () => analyzeProvider.runAnalysis()), vscode.commands.registerCommand("sdd.analyzeReset", () => analyzeProvider.resetSession()), vscode.commands.registerCommand("sdd.refresh", () => treeProvider.refresh()), vscode.commands.registerCommand("sdd.validate", async () => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        await (0, diagnostics_1.runValidation)(root, diagCollection);
        treeProvider.refresh();
        const hasErrors = [...diagCollection].some(([, diags]) => diags.length > 0);
        if (hasErrors) {
            vscode.window.showWarningMessage("SDD: Validierungsfehler – siehe Problems-Panel.");
        }
        else {
            vscode.window.showInformationMessage("SDD: Alles in Ordnung.");
        }
    }), vscode.commands.registerCommand("sdd.updateTrace", async () => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        await (0, cli_1.runSdd)(["trace"], root);
        vscode.window.showInformationMessage("SDD: Traceability-Matrix aktualisiert.");
    }), vscode.commands.registerCommand("sdd.newSpec", async () => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        const title = await vscode.window.showInputBox({ prompt: "Spec-Titel" });
        if (!title) {
            return;
        }
        await (0, cli_1.runSdd)(["new", "spec", title], root);
        treeProvider.refresh();
        vscode.window.showInformationMessage(`SDD: Spec "${title}" angelegt.`);
    }), vscode.commands.registerCommand("sdd.newContract", async () => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        const specId = await vscode.window.showInputBox({ prompt: "Spec-ID (z.B. SPEC-0001)" });
        if (!specId) {
            return;
        }
        const fmt = await vscode.window.showQuickPick(["openapi", "gherkin", "json-schema", "slo-yaml", "asyncapi", "graphql", "grpc", "avro", "protobuf", "markdown"], { placeHolder: "Contract-Format wählen" });
        if (!fmt) {
            return;
        }
        const titleStr = await vscode.window.showInputBox({ prompt: "Titel (optional)" });
        const args = ["new", "contract", "--spec", specId, "--format", fmt];
        if (titleStr) {
            args.push("--title", titleStr);
        }
        await (0, cli_1.runSdd)(args, root);
        treeProvider.refresh();
        vscode.window.showInformationMessage("SDD: Contract angelegt.");
    }), vscode.commands.registerCommand("sdd.newTest", async () => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        const specId = await vscode.window.showInputBox({ prompt: "Spec-ID" });
        if (!specId) {
            return;
        }
        const contractId = await vscode.window.showInputBox({ prompt: "Contract-ID" });
        if (!contractId) {
            return;
        }
        const level = await vscode.window.showQuickPick(["unit", "integration", "contract", "acceptance", "performance", "property"], { placeHolder: "Test-Level wählen" });
        if (!level) {
            return;
        }
        await (0, cli_1.runSdd)(["new", "test", "--spec", specId, "--contract", contractId, "--level", level], root);
        treeProvider.refresh();
        vscode.window.showInformationMessage("SDD: Test angelegt.");
    }), vscode.commands.registerCommand("sdd.newAdr", async () => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        const title = await vscode.window.showInputBox({ prompt: "ADR-Titel" });
        if (!title) {
            return;
        }
        await (0, cli_1.runSdd)(["new", "adr", title], root);
        vscode.window.showInformationMessage(`SDD: ADR "${title}" angelegt.`);
    }), 
    // ── Server Management ─────────────────────────────────────────────────
    vscode.commands.registerCommand("sdd.startWebUI", async () => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        if (server.getStatus() === "running" || server.getStatus() === "starting") {
            const choice = await vscode.window.showQuickPick(["Browser öffnen", "Neustarten", "Abbrechen"], { placeHolder: `Server läuft auf Port ${server.getPort()}` });
            if (choice === "Browser öffnen") {
                vscode.env.openExternal(vscode.Uri.parse(`http://localhost:${server.getPort()}`));
            }
            else if (choice === "Neustarten") {
                vscode.commands.executeCommand("sdd.restartWebUI");
            }
            return;
        }
        try {
            await server.start(root);
            if (vscode.workspace.getConfiguration("sdd").get("webUi.openBrowser", true)) {
                vscode.env.openExternal(vscode.Uri.parse(`http://localhost:${server.getPort()}`));
            }
        }
        catch (e) {
            const msg = e instanceof Error ? e.message : String(e);
            vscode.window.showErrorMessage(`SDD Server: ${msg}`);
            out.show(true);
        }
    }), vscode.commands.registerCommand("sdd.stopWebUI", async () => {
        if (server.getStatus() === "stopped") {
            vscode.window.showInformationMessage("SDD: Server ist bereits gestoppt.");
            return;
        }
        await server.stop();
        vscode.window.showInformationMessage("SDD: Server gestoppt.");
    }), vscode.commands.registerCommand("sdd.restartWebUI", async () => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        await server.stop();
        try {
            await server.start(root);
            if (vscode.workspace.getConfiguration("sdd").get("webUi.openBrowser", true)) {
                vscode.env.openExternal(vscode.Uri.parse(`http://localhost:${server.getPort()}`));
            }
        }
        catch (e) {
            const msg = e instanceof Error ? e.message : String(e);
            vscode.window.showErrorMessage(`SDD Server Restart: ${msg}`);
        }
    }), vscode.commands.registerCommand("sdd.openWebUI", async () => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        if (server.getStatus() !== "running") {
            const choice = await vscode.window.showInformationMessage("SDD-Server läuft nicht. Jetzt starten?", "Starten", "Abbrechen");
            if (choice !== "Starten") {
                return;
            }
            try {
                await server.start(root);
            }
            catch (e) {
                vscode.window.showErrorMessage(`SDD Server: ${e instanceof Error ? e.message : String(e)}`);
                return;
            }
        }
        vscode.env.openExternal(vscode.Uri.parse(`http://localhost:${server.getPort()}`));
    }), vscode.commands.registerCommand("sdd.showOutput", () => out.show(true)), 
    // ── Pipeline Execute ──────────────────────────────────────────────────
    vscode.commands.registerCommand("sdd.executeCurrentSpec", async (node) => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        let specId;
        // Called from TreeView inline button: node is the SddNode
        if (node?.id_str) {
            specId = node.id_str;
        }
        else {
            // Called from command palette: read from active editor
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                const fm = (0, frontmatter_1.parseFrontmatter)(editor.document.fileName);
                specId = fm.id;
            }
            // If still no ID: fallback to Quick Pick
            if (!specId) {
                const approved = (0, tree_1.collectApprovedSpecs)(root);
                if (approved.length === 0) {
                    vscode.window.showWarningMessage("SDD: Keine approved Specs gefunden.");
                    return;
                }
                const picked = await vscode.window.showQuickPick(approved.map((s) => ({ label: s.id, description: s.title })), { placeHolder: "Spec auswählen" });
                if (!picked) {
                    return;
                }
                specId = picked.label;
            }
        }
        // Validate status from file
        const fm = readSpecFrontmatterById(root, specId);
        if (fm && fm.status !== "approved") {
            vscode.window.showWarningMessage(`SDD: ${specId} hat Status '${fm.status}' – nur approved Specs können ausgeführt werden.`);
            return;
        }
        // Ensure server is running
        if (server.getStatus() !== "running") {
            const choice = await vscode.window.showInformationMessage("SDD-Server läuft nicht. Jetzt starten?", "Starten", "Abbrechen");
            if (choice !== "Starten") {
                return;
            }
            try {
                await server.start(root);
            }
            catch (e) {
                vscode.window.showErrorMessage(`SDD Server: ${e instanceof Error ? e.message : String(e)}`);
                return;
            }
        }
        await runPipeline(specId, pipelineClient, treeProvider, out);
    }), vscode.commands.registerCommand("sdd.executeSpec", async () => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        const approved = (0, tree_1.collectApprovedSpecs)(root);
        if (approved.length === 0) {
            vscode.window.showWarningMessage("SDD: Keine approved Specs gefunden.");
            return;
        }
        const picked = await vscode.window.showQuickPick(approved.map((s) => ({ label: s.id, description: s.title })), { placeHolder: "Spec für Execute auswählen" });
        if (!picked) {
            return;
        }
        if (server.getStatus() !== "running") {
            const choice = await vscode.window.showInformationMessage("SDD-Server läuft nicht. Jetzt starten?", "Starten", "Abbrechen");
            if (choice !== "Starten") {
                return;
            }
            try {
                await server.start(root);
            }
            catch (e) {
                vscode.window.showErrorMessage(`SDD Server: ${e instanceof Error ? e.message : String(e)}`);
                return;
            }
        }
        await runPipeline(picked.label, pipelineClient, treeProvider, out);
    }), vscode.commands.registerCommand("sdd.abortPipeline", async () => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        if (server.getStatus() !== "running") {
            vscode.window.showWarningMessage("SDD: Server läuft nicht.");
            return;
        }
        // Find running pipelines from tree state (we'd need to track them)
        const runId = await vscode.window.showInputBox({ prompt: "Run-ID zum Abbrechen (z.B. SPEC-0007-1747...)" });
        if (!runId) {
            return;
        }
        try {
            await pipelineClient.abort(runId);
            vscode.window.showInformationMessage(`SDD: Pipeline ${runId} abgebrochen.`);
        }
        catch (e) {
            vscode.window.showErrorMessage(`SDD Abort: ${e instanceof Error ? e.message : String(e)}`);
        }
    }), 
    // ── CLI Wrapper Commands ──────────────────────────────────────────────
    vscode.commands.registerCommand("sdd.reviewContract", async () => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        const conId = await vscode.window.showInputBox({ prompt: "Contract-ID (z.B. CON-0012)" });
        if (!conId) {
            return;
        }
        out.show(true);
        out.appendLine(`\n[SDD] sdd review-contract ${conId}`);
        try {
            const { stdout, stderr } = await (0, cli_1.runSdd)(["review-contract", conId], root);
            out.append(stdout);
            if (stderr) {
                out.append(stderr);
            }
        }
        catch (e) {
            out.appendLine(`Fehler: ${e instanceof Error ? e.message : String(e)}`);
        }
    }), vscode.commands.registerCommand("sdd.reviewPending", async () => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        out.show(true);
        out.appendLine("\n[SDD] sdd review-pending");
        await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: "SDD: Contract-Review läuft…", cancellable: false }, async () => {
            try {
                const { stdout, stderr } = await (0, cli_1.runSdd)(["review-pending"], root);
                out.append(stdout);
                if (stderr) {
                    out.append(stderr);
                }
            }
            catch (e) {
                out.appendLine(`Fehler: ${e instanceof Error ? e.message : String(e)}`);
            }
        });
    }), vscode.commands.registerCommand("sdd.estimateCurrentSpec", async () => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        const editor = vscode.window.activeTextEditor;
        let specId;
        if (editor) {
            const fm = (0, frontmatter_1.parseFrontmatter)(editor.document.fileName);
            specId = fm.id;
        }
        if (!specId) {
            specId = await vscode.window.showInputBox({ prompt: "Spec-ID (z.B. SPEC-0007)" });
        }
        if (!specId) {
            return;
        }
        out.show(true);
        out.appendLine(`\n[SDD] sdd estimate ${specId}`);
        try {
            const { stdout } = await (0, cli_1.runSdd)(["estimate", specId], root);
            out.append(stdout);
            // Show cost summary as notification (first line with cost)
            const costLine = stdout.split("\n").find((l) => l.includes("$") || l.includes("€") || l.toLowerCase().includes("token"));
            if (costLine) {
                vscode.window.showInformationMessage(`${specId}: ${costLine.trim()}`);
            }
        }
        catch (e) {
            out.appendLine(`Fehler: ${e instanceof Error ? e.message : String(e)}`);
        }
    }), vscode.commands.registerCommand("sdd.statusCheck", async () => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        out.show(true);
        out.appendLine("\n[SDD] sdd status-check");
        const { stdout, stderr } = await (0, cli_1.runSdd)(["status-check"], root).catch((e) => ({
            stdout: "",
            stderr: e instanceof Error ? e.message : String(e),
        }));
        out.append(stdout);
        if (stderr) {
            out.append(stderr);
        }
    }), vscode.commands.registerCommand("sdd.obsidianExport", async () => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        out.show(true);
        out.appendLine("\n[SDD] sdd obsidian export");
        await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: "SDD: Obsidian Export…", cancellable: false }, async () => {
            const { stdout, stderr } = await (0, cli_1.runSdd)(["obsidian", "export"], root).catch((e) => ({
                stdout: "",
                stderr: e instanceof Error ? e.message : String(e),
            }));
            out.append(stdout);
            if (stderr) {
                out.append(stderr);
            }
        });
        vscode.window.showInformationMessage("SDD: Obsidian Export abgeschlossen.");
    }), vscode.commands.registerCommand("sdd.obsidianImport", async () => {
        if (!root) {
            vscode.window.showWarningMessage("SDD: Kein Projekt gefunden.");
            return;
        }
        out.show(true);
        out.appendLine("\n[SDD] sdd obsidian import");
        await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: "SDD: Obsidian Import…", cancellable: false }, async () => {
            const { stdout, stderr } = await (0, cli_1.runSdd)(["obsidian", "import"], root).catch((e) => ({
                stdout: "",
                stderr: e instanceof Error ? e.message : String(e),
            }));
            out.append(stdout);
            if (stderr) {
                out.append(stderr);
            }
        });
        vscode.window.showInformationMessage("SDD: Obsidian Import abgeschlossen.");
    }));
    // ── Project Root Discovery ────────────────────────────────────────────────
    const folders = vscode.workspace.workspaceFolders ?? [];
    out.appendLine(`Workspace-Ordner: ${folders.map((f) => f.uri.fsPath).join(", ") || "(keine)"}`);
    for (const folder of folders) {
        const found = await (0, cli_1.findProjectRoot)(folder.uri.fsPath);
        if (found) {
            root = found;
            out.appendLine(`SDD-Projekt gefunden: ${root}`);
            treeProvider.setRoot(root);
            if (vscode.workspace.getConfiguration("sdd").get("showCodeLens", true)) {
                context.subscriptions.push(vscode.languages.registerCodeLensProvider({ language: "markdown", scheme: "file" }, new codelens_1.SddCodeLensProvider()));
            }
            context.subscriptions.push(vscode.languages.registerDefinitionProvider({ language: "markdown", scheme: "file" }, new definition_1.SddDefinitionProvider(root)), vscode.languages.registerHoverProvider({ language: "markdown", scheme: "file" }, new definition_1.SddHoverProvider(root)));
            context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(async (doc) => {
                if (!doc.fileName.endsWith(".md") || !doc.fileName.startsWith(root)) {
                    return;
                }
                if (vscode.workspace.getConfiguration("sdd").get("validateOnSave", true)) {
                    await (0, diagnostics_1.runValidation)(root, diagCollection);
                    treeProvider.refresh();
                }
                if (vscode.workspace.getConfiguration("sdd").get("analyzeOnSave", false)) {
                    analyzeProvider.runAnalysis();
                }
            }));
            const interval = vscode.workspace.getConfiguration("sdd").get("treeViewRefreshInterval", 0);
            if (interval > 0) {
                const timer = setInterval(() => treeProvider.refresh(), interval * 1000);
                context.subscriptions.push({ dispose: () => clearInterval(timer) });
            }
            await (0, diagnostics_1.runValidation)(root, diagCollection);
            // Auto-start server if configured
            if (vscode.workspace.getConfiguration("sdd").get("webUi.autoStart", false)) {
                server.start(root).catch(() => { });
            }
            break;
        }
    }
    if (!root) {
        out.appendLine("Kein SDD-Projekt (.sdd/config.yaml) in den Workspace-Ordnern gefunden.");
        out.show(true);
    }
}
function deactivate() {
    server_1.ServerManager.getInstance(out).dispose();
}
// ── Helpers ───────────────────────────────────────────────────────────────────
function updateStatusBar(item, server) {
    const status = server.getStatus();
    switch (status) {
        case "stopped":
            item.text = "$(circle-outline) SDD";
            item.tooltip = "SDD Server gestoppt – klicken zum Starten";
            item.command = "sdd.startWebUI";
            item.backgroundColor = undefined;
            break;
        case "starting":
            item.text = "$(sync~spin) SDD";
            item.tooltip = "SDD Server startet…";
            item.command = undefined;
            item.backgroundColor = undefined;
            break;
        case "running":
            item.text = `$(zap) SDD :${server.getPort()}`;
            item.tooltip = `SDD Server läuft auf http://localhost:${server.getPort()} – klicken zum Öffnen`;
            item.command = "sdd.openWebUI";
            item.backgroundColor = undefined;
            break;
        case "error":
            item.text = "$(error) SDD";
            item.tooltip = "SDD Server Fehler – klicken für Output";
            item.command = "sdd.showOutput";
            item.backgroundColor = new vscode.ThemeColor("statusBarItem.errorBackground");
            break;
    }
}
function readSpecFrontmatterById(root, specId) {
    const path = require("path");
    const fs = require("fs");
    const { parseFrontmatter: pf } = require("./frontmatter");
    const specsDir = path.join(root, ".sdd", "specs");
    try {
        const files = fs.readdirSync(specsDir);
        const file = files.find((f) => f.startsWith(specId) && f.endsWith(".md"));
        if (!file) {
            return null;
        }
        return pf(path.join(specsDir, file));
    }
    catch {
        return null;
    }
}
const POLL_INTERVAL_MS = 5000;
async function runPipeline(specId, client, tree, out) {
    let runId;
    try {
        runId = await client.orchestrate(specId);
        out.appendLine(`\n[Pipeline] ${specId} gestartet – run_id: ${runId}`);
    }
    catch (e) {
        const err = e;
        if (err.status === 409) {
            vscode.window.showWarningMessage(`SDD: Pipeline für ${specId} läuft bereits.`);
        }
        else if (err.status === 422) {
            vscode.window.showWarningMessage(`SDD: ${specId} ist nicht approved.`);
        }
        else if (err.status === 503) {
            vscode.window.showErrorMessage("SDD: Claude CLI nicht gefunden oder nicht eingeloggt.");
        }
        else {
            vscode.window.showErrorMessage(`SDD Execute: ${err.message}`);
        }
        return;
    }
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `Pipeline: ${specId}`,
        cancellable: true,
    }, async (progress, token) => {
        token.onCancellationRequested(async () => {
            try {
                await client.abort(runId);
                out.appendLine(`[Pipeline] ${runId} abgebrochen.`);
            }
            catch {
                // ignore
            }
        });
        while (true) {
            let state;
            try {
                state = await client.getRun(runId);
            }
            catch {
                // Server weg oder TTL abgelaufen
                tree.clearPipelineRun(specId);
                break;
            }
            tree.setPipelineRun(specId, state);
            const attempts = Array.isArray(state.attempts) ? state.attempts.length : 0;
            progress.report({
                message: `${state.current_step} · Attempt ${attempts}/${state.max_attempts}`,
            });
            out.appendLine(`[Pipeline] ${state.current_step} (${state.status})`);
            if (pipeline_1.TERMINAL_STATUSES.includes(state.status)) {
                // Keep tree icon for 30 s then clear
                setTimeout(() => tree.clearPipelineRun(specId), 30000);
                if (state.status === "labeled" || state.status === "merged") {
                    const prUrl = state.report?.pr_url;
                    const msg = prUrl
                        ? `${specId} implementiert`
                        : `${specId} implementiert (dry-run)`;
                    const action = prUrl ? await vscode.window.showInformationMessage(msg, "PR öffnen") : undefined;
                    if (action === "PR öffnen" && prUrl) {
                        vscode.env.openExternal(vscode.Uri.parse(prUrl));
                    }
                }
                else if (state.status === "failed") {
                    const reason = state.report?.reason ?? "Unbekannter Fehler";
                    vscode.window.showErrorMessage(`${specId} Pipeline fehlgeschlagen: ${reason}`);
                }
                else if (state.status === "aborted") {
                    vscode.window.showInformationMessage(`${specId}: Pipeline abgebrochen.`);
                }
                break;
            }
            // Wait before next poll
            await delay(POLL_INTERVAL_MS);
            if (token.isCancellationRequested) {
                break;
            }
        }
    });
}
function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}
//# sourceMappingURL=extension.js.map