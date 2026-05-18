import * as vscode from "vscode";
import { findProjectRoot, runSdd } from "./cli";
import { SddTreeProvider, SddNode, collectApprovedSpecs } from "./tree";
import { createDiagnosticCollection, runValidation } from "./diagnostics";
import { SddCodeLensProvider } from "./codelens";
import { SddDefinitionProvider, SddHoverProvider } from "./definition";
import { SddAnalyzeViewProvider } from "./analyzeView";
import { ServerManager } from "./server";
import { PipelineClient, PipelineRunState, TERMINAL_STATUSES } from "./pipeline";
import { parseFrontmatter } from "./frontmatter";

const out = vscode.window.createOutputChannel("SDD Framer");

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  out.appendLine("SDD Framer aktiviert.");

  const server = ServerManager.getInstance(out);
  const pipelineClient = new PipelineClient(() => {
    return server.getBaseUrl() ?? vscode.workspace.getConfiguration("sdd").get<string>("webApiUrl", "http://localhost:8000");
  });

  // Status Bar
  const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  updateStatusBar(statusBar, server);
  server.onDidChangeStatus(() => updateStatusBar(statusBar, server), undefined, context.subscriptions);
  statusBar.show();
  context.subscriptions.push(statusBar);

  // TreeView
  const treeProvider = new SddTreeProvider();
  context.subscriptions.push(
    vscode.window.registerTreeDataProvider("sddTree", treeProvider),
    out
  );

  // Analyze-Panel
  const analyzeProvider = new SddAnalyzeViewProvider(context);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(SddAnalyzeViewProvider.viewId, analyzeProvider)
  );

  // Diagnostics
  const diagCollection = createDiagnosticCollection();
  context.subscriptions.push(diagCollection);

  let root = "";

  // ── Commands ─────────────────────────────────────────────────────────────

  context.subscriptions.push(
    // Existing
    vscode.commands.registerCommand("sdd.analyzeDoc", () => analyzeProvider.runAnalysis()),
    vscode.commands.registerCommand("sdd.analyzeReset", () => analyzeProvider.resetSession()),
    vscode.commands.registerCommand("sdd.refresh", () => treeProvider.refresh()),

    vscode.commands.registerCommand("sdd.validate", async () => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }
      await runValidation(root, diagCollection);
      treeProvider.refresh();
      const hasErrors = [...diagCollection].some(([, diags]) => diags.length > 0);
      if (hasErrors) {
        vscode.window.showWarningMessage("SDD: Validierungsfehler – siehe Problems-Panel.");
      } else {
        vscode.window.showInformationMessage("SDD: Alles in Ordnung.");
      }
    }),

    vscode.commands.registerCommand("sdd.updateTrace", async () => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }
      await runSdd(["trace"], root);
      vscode.window.showInformationMessage("SDD: Traceability-Matrix aktualisiert.");
    }),

    vscode.commands.registerCommand("sdd.newSpec", async () => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }
      const title = await vscode.window.showInputBox({ prompt: "Spec-Titel" });
      if (!title) { return; }
      await runSdd(["new", "spec", title], root);
      treeProvider.refresh();
      vscode.window.showInformationMessage(`SDD: Spec "${title}" angelegt.`);
    }),

    vscode.commands.registerCommand("sdd.newContract", async () => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }
      const specId = await vscode.window.showInputBox({ prompt: "Spec-ID (z.B. SPEC-0001)" });
      if (!specId) { return; }
      const fmt = await vscode.window.showQuickPick(
        ["openapi", "gherkin", "json-schema", "slo-yaml", "asyncapi", "graphql", "grpc", "avro", "protobuf", "markdown"],
        { placeHolder: "Contract-Format wählen" }
      );
      if (!fmt) { return; }
      const titleStr = await vscode.window.showInputBox({ prompt: "Titel (optional)" });
      const args = ["new", "contract", "--spec", specId, "--format", fmt];
      if (titleStr) { args.push("--title", titleStr); }
      await runSdd(args, root);
      treeProvider.refresh();
      vscode.window.showInformationMessage("SDD: Contract angelegt.");
    }),

    vscode.commands.registerCommand("sdd.newTest", async () => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }
      const specId = await vscode.window.showInputBox({ prompt: "Spec-ID" });
      if (!specId) { return; }
      const contractId = await vscode.window.showInputBox({ prompt: "Contract-ID" });
      if (!contractId) { return; }
      const level = await vscode.window.showQuickPick(
        ["unit", "integration", "contract", "acceptance", "performance", "property"],
        { placeHolder: "Test-Level wählen" }
      );
      if (!level) { return; }
      await runSdd(["new", "test", "--spec", specId, "--contract", contractId, "--level", level], root);
      treeProvider.refresh();
      vscode.window.showInformationMessage("SDD: Test angelegt.");
    }),

    vscode.commands.registerCommand("sdd.newAdr", async () => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }
      const title = await vscode.window.showInputBox({ prompt: "ADR-Titel" });
      if (!title) { return; }
      await runSdd(["new", "adr", title], root);
      vscode.window.showInformationMessage(`SDD: ADR "${title}" angelegt.`);
    }),

    // ── Server Management ─────────────────────────────────────────────────

    vscode.commands.registerCommand("sdd.startWebUI", async () => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }

      if (server.getStatus() === "running" || server.getStatus() === "starting") {
        const choice = await vscode.window.showQuickPick(
          ["Browser öffnen", "Neustarten", "Abbrechen"],
          { placeHolder: `Server läuft auf Port ${server.getPort()}` }
        );
        if (choice === "Browser öffnen") {
          vscode.env.openExternal(vscode.Uri.parse(server.getBaseUrl()!));
        } else if (choice === "Neustarten") {
          vscode.commands.executeCommand("sdd.restartWebUI");
        }
        return;
      }

      try {
        await server.start(root);
        if (vscode.workspace.getConfiguration("sdd").get<boolean>("webUi.openBrowser", true)) {
          const url = server.getBaseUrl()!;
          out.appendLine(`[SDD] openExternal → ${url}`);
          vscode.env.openExternal(vscode.Uri.parse(url));
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        vscode.window.showErrorMessage(`SDD Server: ${msg}`);
        out.show(true);
      }
    }),

    vscode.commands.registerCommand("sdd.stopWebUI", async () => {
      if (server.getStatus() === "stopped") {
        vscode.window.showInformationMessage("SDD: Server ist bereits gestoppt.");
        return;
      }
      await server.stop();
      vscode.window.showInformationMessage("SDD: Server gestoppt.");
    }),

    vscode.commands.registerCommand("sdd.restartWebUI", async () => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }
      await server.stop();
      try {
        await server.start(root);
        if (vscode.workspace.getConfiguration("sdd").get<boolean>("webUi.openBrowser", true)) {
          vscode.env.openExternal(vscode.Uri.parse(server.getBaseUrl()!));
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        vscode.window.showErrorMessage(`SDD Server Restart: ${msg}`);
      }
    }),

    vscode.commands.registerCommand("sdd.openWebUI", async () => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }
      if (server.getStatus() !== "running") {
        const choice = await vscode.window.showInformationMessage(
          "SDD-Server läuft nicht. Jetzt starten?",
          "Starten",
          "Abbrechen"
        );
        if (choice !== "Starten") { return; }
        try {
          await server.start(root);
        } catch (e) {
          vscode.window.showErrorMessage(`SDD Server: ${e instanceof Error ? e.message : String(e)}`);
          return;
        }
      }
      vscode.env.openExternal(vscode.Uri.parse(server.getBaseUrl()!));
    }),

    vscode.commands.registerCommand("sdd.showOutput", () => out.show(true)),

    // ── Pipeline Execute ──────────────────────────────────────────────────

    vscode.commands.registerCommand("sdd.executeCurrentSpec", async (node?: SddNode) => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }

      let specId: string | undefined;

      // Called from TreeView inline button: node is the SddNode
      if (node?.id_str) {
        specId = node.id_str;
      } else {
        // Called from command palette: read from active editor
        const editor = vscode.window.activeTextEditor;
        if (editor) {
          const fm = parseFrontmatter(editor.document.fileName);
          specId = fm.id as string | undefined;
        }
        // If still no ID: fallback to Quick Pick
        if (!specId) {
          const approved = collectApprovedSpecs(root);
          if (approved.length === 0) {
            vscode.window.showWarningMessage("SDD: Keine approved Specs gefunden.");
            return;
          }
          const picked = await vscode.window.showQuickPick(
            approved.map((s) => ({ label: s.id, description: s.title })),
            { placeHolder: "Spec auswählen" }
          );
          if (!picked) { return; }
          specId = picked.label;
        }
      }

      // Validate status from file
      const fm = readSpecFrontmatterById(root, specId);
      if (fm && fm.status !== "approved") {
        vscode.window.showWarningMessage(
          `SDD: ${specId} hat Status '${fm.status}' – nur approved Specs können ausgeführt werden.`
        );
        return;
      }

      // Ensure server is running
      if (server.getStatus() !== "running") {
        const choice = await vscode.window.showInformationMessage(
          "SDD-Server läuft nicht. Jetzt starten?",
          "Starten",
          "Abbrechen"
        );
        if (choice !== "Starten") { return; }
        try {
          await server.start(root);
        } catch (e) {
          vscode.window.showErrorMessage(`SDD Server: ${e instanceof Error ? e.message : String(e)}`);
          return;
        }
      }

      await runPipeline(specId, pipelineClient, treeProvider, out);
    }),

    vscode.commands.registerCommand("sdd.executeSpec", async () => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }

      const approved = collectApprovedSpecs(root);
      if (approved.length === 0) {
        vscode.window.showWarningMessage("SDD: Keine approved Specs gefunden.");
        return;
      }
      const picked = await vscode.window.showQuickPick(
        approved.map((s) => ({ label: s.id, description: s.title })),
        { placeHolder: "Spec für Execute auswählen" }
      );
      if (!picked) { return; }

      if (server.getStatus() !== "running") {
        const choice = await vscode.window.showInformationMessage(
          "SDD-Server läuft nicht. Jetzt starten?",
          "Starten",
          "Abbrechen"
        );
        if (choice !== "Starten") { return; }
        try {
          await server.start(root);
        } catch (e) {
          vscode.window.showErrorMessage(`SDD Server: ${e instanceof Error ? e.message : String(e)}`);
          return;
        }
      }

      await runPipeline(picked.label, pipelineClient, treeProvider, out);
    }),

    vscode.commands.registerCommand("sdd.abortPipeline", async () => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }
      if (server.getStatus() !== "running") {
        vscode.window.showWarningMessage("SDD: Server läuft nicht.");
        return;
      }

      // Find running pipelines from tree state (we'd need to track them)
      const runId = await vscode.window.showInputBox({ prompt: "Run-ID zum Abbrechen (z.B. SPEC-0007-1747...)" });
      if (!runId) { return; }
      try {
        await pipelineClient.abort(runId);
        vscode.window.showInformationMessage(`SDD: Pipeline ${runId} abgebrochen.`);
      } catch (e) {
        vscode.window.showErrorMessage(`SDD Abort: ${e instanceof Error ? e.message : String(e)}`);
      }
    }),

    // ── CLI Wrapper Commands ──────────────────────────────────────────────

    vscode.commands.registerCommand("sdd.reviewContract", async () => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }
      const conId = await vscode.window.showInputBox({ prompt: "Contract-ID (z.B. CON-0012)" });
      if (!conId) { return; }
      out.show(true);
      out.appendLine(`\n[SDD] sdd review-contract ${conId}`);
      try {
        const { stdout, stderr } = await runSdd(["review-contract", conId], root);
        out.append(stdout);
        if (stderr) { out.append(stderr); }
      } catch (e) {
        out.appendLine(`Fehler: ${e instanceof Error ? e.message : String(e)}`);
      }
    }),

    vscode.commands.registerCommand("sdd.reviewPending", async () => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }
      out.show(true);
      out.appendLine("\n[SDD] sdd review-pending");
      await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: "SDD: Contract-Review läuft…", cancellable: false },
        async () => {
          try {
            const { stdout, stderr } = await runSdd(["review-pending"], root);
            out.append(stdout);
            if (stderr) { out.append(stderr); }
          } catch (e) {
            out.appendLine(`Fehler: ${e instanceof Error ? e.message : String(e)}`);
          }
        }
      );
    }),

    vscode.commands.registerCommand("sdd.estimateCurrentSpec", async () => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }
      const editor = vscode.window.activeTextEditor;
      let specId: string | undefined;
      if (editor) {
        const fm = parseFrontmatter(editor.document.fileName);
        specId = fm.id as string | undefined;
      }
      if (!specId) {
        specId = await vscode.window.showInputBox({ prompt: "Spec-ID (z.B. SPEC-0007)" });
      }
      if (!specId) { return; }
      out.show(true);
      out.appendLine(`\n[SDD] sdd estimate ${specId}`);
      try {
        const { stdout } = await runSdd(["estimate", specId], root);
        out.append(stdout);
        // Show cost summary as notification (first line with cost)
        const costLine = stdout.split("\n").find((l) => l.includes("$") || l.includes("€") || l.toLowerCase().includes("token"));
        if (costLine) {
          vscode.window.showInformationMessage(`${specId}: ${costLine.trim()}`);
        }
      } catch (e) {
        out.appendLine(`Fehler: ${e instanceof Error ? e.message : String(e)}`);
      }
    }),

    vscode.commands.registerCommand("sdd.statusCheck", async () => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }
      out.show(true);
      out.appendLine("\n[SDD] sdd status-check");
      const { stdout, stderr } = await runSdd(["status-check"], root).catch((e) => ({
        stdout: "",
        stderr: e instanceof Error ? e.message : String(e),
      }));
      out.append(stdout);
      if (stderr) { out.append(stderr); }
    }),

    vscode.commands.registerCommand("sdd.obsidianExport", async () => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }
      out.show(true);
      out.appendLine("\n[SDD] sdd obsidian export");
      await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: "SDD: Obsidian Export…", cancellable: false },
        async () => {
          const { stdout, stderr } = await runSdd(["obsidian", "export"], root).catch((e) => ({
            stdout: "",
            stderr: e instanceof Error ? e.message : String(e),
          }));
          out.append(stdout);
          if (stderr) { out.append(stderr); }
        }
      );
      vscode.window.showInformationMessage("SDD: Obsidian Export abgeschlossen.");
    }),

    vscode.commands.registerCommand("sdd.obsidianImport", async () => {
      if (!root) { vscode.window.showWarningMessage("SDD: Kein Projekt gefunden."); return; }
      out.show(true);
      out.appendLine("\n[SDD] sdd obsidian import");
      await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: "SDD: Obsidian Import…", cancellable: false },
        async () => {
          const { stdout, stderr } = await runSdd(["obsidian", "import"], root).catch((e) => ({
            stdout: "",
            stderr: e instanceof Error ? e.message : String(e),
          }));
          out.append(stdout);
          if (stderr) { out.append(stderr); }
        }
      );
      vscode.window.showInformationMessage("SDD: Obsidian Import abgeschlossen.");
    })
  );

  // ── Project Root Discovery ────────────────────────────────────────────────

  const folders = vscode.workspace.workspaceFolders ?? [];
  out.appendLine(`Workspace-Ordner: ${folders.map((f) => f.uri.fsPath).join(", ") || "(keine)"}`);

  for (const folder of folders) {
    const found = await findProjectRoot(folder.uri.fsPath);
    if (found) {
      root = found;
      out.appendLine(`SDD-Projekt gefunden: ${root}`);
      treeProvider.setRoot(root);

      if (vscode.workspace.getConfiguration("sdd").get<boolean>("showCodeLens", true)) {
        context.subscriptions.push(
          vscode.languages.registerCodeLensProvider(
            { language: "markdown", scheme: "file" },
            new SddCodeLensProvider()
          )
        );
      }

      context.subscriptions.push(
        vscode.languages.registerDefinitionProvider(
          { language: "markdown", scheme: "file" },
          new SddDefinitionProvider(root)
        ),
        vscode.languages.registerHoverProvider(
          { language: "markdown", scheme: "file" },
          new SddHoverProvider(root)
        )
      );

      context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument(async (doc) => {
          if (!doc.fileName.endsWith(".md") || !doc.fileName.startsWith(root)) { return; }
          if (vscode.workspace.getConfiguration("sdd").get<boolean>("validateOnSave", true)) {
            await runValidation(root, diagCollection);
            treeProvider.refresh();
          }
          if (vscode.workspace.getConfiguration("sdd").get<boolean>("analyzeOnSave", false)) {
            analyzeProvider.runAnalysis();
          }
        })
      );

      const interval = vscode.workspace.getConfiguration("sdd").get<number>("treeViewRefreshInterval", 0);
      if (interval > 0) {
        const timer = setInterval(() => treeProvider.refresh(), interval * 1000);
        context.subscriptions.push({ dispose: () => clearInterval(timer) });
      }

      await runValidation(root, diagCollection);

      // Auto-start server if configured
      if (vscode.workspace.getConfiguration("sdd").get<boolean>("webUi.autoStart", false)) {
        server.start(root).catch(() => { /* silent – user can start manually */ });
      }

      break;
    }
  }

  if (!root) {
    out.appendLine("Kein SDD-Projekt (.sdd/config.yaml) in den Workspace-Ordnern gefunden.");
    out.show(true);
  }
}

export function deactivate(): void {
  ServerManager.getInstance(out).dispose();
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function updateStatusBar(item: vscode.StatusBarItem, server: ServerManager): void {
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
      item.tooltip = `SDD Server läuft auf ${server.getBaseUrl()} – klicken zum Öffnen`;
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

function readSpecFrontmatterById(root: string, specId: string): Record<string, unknown> | null {
  const path = require("path") as typeof import("path");
  const fs = require("fs") as typeof import("fs");
  const { parseFrontmatter: pf } = require("./frontmatter") as typeof import("./frontmatter");
  const specsDir = path.join(root, ".sdd", "specs");
  try {
    const files = fs.readdirSync(specsDir) as string[];
    const file = files.find((f: string) => f.startsWith(specId) && f.endsWith(".md"));
    if (!file) { return null; }
    return pf(path.join(specsDir, file)) as Record<string, unknown>;
  } catch {
    return null;
  }
}

const POLL_INTERVAL_MS = 5_000;

async function runPipeline(
  specId: string,
  client: PipelineClient,
  tree: SddTreeProvider,
  out: vscode.OutputChannel
): Promise<void> {
  let runId: string;

  try {
    runId = await client.orchestrate(specId);
    out.appendLine(`\n[Pipeline] ${specId} gestartet – run_id: ${runId}`);
  } catch (e) {
    const err = e as Error & { status?: number };
    if (err.status === 409) {
      vscode.window.showWarningMessage(`SDD: Pipeline für ${specId} läuft bereits.`);
    } else if (err.status === 422) {
      vscode.window.showWarningMessage(`SDD: ${specId} ist nicht approved.`);
    } else if (err.status === 503) {
      vscode.window.showErrorMessage("SDD: Claude CLI nicht gefunden oder nicht eingeloggt.");
    } else {
      vscode.window.showErrorMessage(`SDD Execute: ${err.message}`);
    }
    return;
  }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: `Pipeline: ${specId}`,
      cancellable: true,
    },
    async (progress, token) => {
      token.onCancellationRequested(async () => {
        try {
          await client.abort(runId);
          out.appendLine(`[Pipeline] ${runId} abgebrochen.`);
        } catch {
          // ignore
        }
      });

      while (true) {
        let state: PipelineRunState;
        try {
          state = await client.getRun(runId);
        } catch {
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

        if ((TERMINAL_STATUSES as string[]).includes(state.status)) {
          // Keep tree icon for 30 s then clear
          setTimeout(() => tree.clearPipelineRun(specId), 30_000);

          if (state.status === "labeled" || state.status === "merged") {
            const prUrl = state.report?.pr_url;
            const msg = prUrl
              ? `${specId} implementiert`
              : `${specId} implementiert (dry-run)`;
            const action = prUrl ? await vscode.window.showInformationMessage(msg, "PR öffnen") : undefined;
            if (action === "PR öffnen" && prUrl) {
              vscode.env.openExternal(vscode.Uri.parse(prUrl));
            }
          } else if (state.status === "failed") {
            const reason = state.report?.reason ?? "Unbekannter Fehler";
            vscode.window.showErrorMessage(`${specId} Pipeline fehlgeschlagen: ${reason}`);
          } else if (state.status === "aborted") {
            vscode.window.showInformationMessage(`${specId}: Pipeline abgebrochen.`);
          }
          break;
        }

        // Wait before next poll
        await delay(POLL_INTERVAL_MS);
        if (token.isCancellationRequested) { break; }
      }
    }
  );
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
