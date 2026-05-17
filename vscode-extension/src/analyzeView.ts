import * as vscode from "vscode";
import * as path from "path";
import { getServerUrl } from "./server";

interface AnsweredQuestion {
  id: string;
  answer: string;
}

interface Question {
  id: string;
  section: string;
  text: string;
  severity: "error" | "warning" | "suggestion";
}

interface Issue {
  section: string;
  text: string;
  severity: "error" | "warning";
}

interface Suggestion {
  text: string;
}

interface AnalyzeResponse {
  session_id: string;
  questions: Question[];
  issues: Issue[];
  suggestions: Suggestion[];
}

function docTypeFromPath(filePath: string): "spec" | "contract" | null {
  const base = path.basename(filePath);
  if (base.startsWith("SPEC-")) return "spec";
  if (base.startsWith("CON-")) return "contract";
  return null;
}

function docIdFromPath(filePath: string): string {
  const base = path.basename(filePath, ".md");
  // SPEC-0001-some-title → SPEC-0001
  const m = base.match(/^((?:SPEC|CON|TST|ADR)-\d+)/);
  return m ? m[1] : base;
}

function apiUrl(): string {
  return getServerUrl();
}

export class SddAnalyzeViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewId = "sddAnalyze";

  private _view?: vscode.WebviewView;
  private _sessionId: string | null = null;
  private _answered: AnsweredQuestion[] = [];
  private _currentDocId: string | null = null;

  constructor(private readonly _context: vscode.ExtensionContext) {}

  resolveWebviewView(
    view: vscode.WebviewView,
    _ctx: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this._view = view;
    view.webview.options = { enableScripts: true };
    this._render("idle");

    view.webview.onDidReceiveMessage((msg) => {
      switch (msg.type) {
        case "analyze":
          this.runAnalysis();
          break;
        case "answer":
          this._answered = [
            ...this._answered.filter((a) => a.id !== msg.id),
            { id: msg.id, answer: msg.answer },
          ];
          break;
        case "reanalyze":
          this.runAnalysis();
          break;
      }
    }, undefined, this._context.subscriptions);
  }

  async runAnalysis(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      this._render("no-editor");
      return;
    }

    const filePath = editor.document.fileName;
    const docType = docTypeFromPath(filePath);
    if (!docType) {
      this._render("not-sdd");
      return;
    }

    const docId = docIdFromPath(filePath);
    if (docId !== this._currentDocId) {
      this._sessionId = null;
      this._answered = [];
      this._currentDocId = docId;
    }

    const content = editor.document.getText();
    this._render("loading", { docId });

    try {
      const body: Record<string, unknown> = {
        content,
        doc_type: docType,
        answered_questions: this._answered,
      };
      if (this._sessionId) body.session_id = this._sessionId;

      const resp = await fetch(`${apiUrl()}/api/docs/${docId}/analyze`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({})) as Record<string, unknown>;
        const detail = err.detail as Record<string, unknown> | undefined;
        if (detail?.error === "claude_not_found") {
          this._render("claude-missing");
          return;
        }
        throw new Error(`HTTP ${resp.status}: ${JSON.stringify(err)}`);
      }

      const data = await resp.json() as AnalyzeResponse;
      this._sessionId = data.session_id;
      this._render("result", { docId, docType, data, answered: this._answered });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      const isConnErr = msg.includes("ECONNREFUSED") || msg.includes("fetch");
      this._render("error", { message: isConnErr ? "Web API nicht erreichbar. Starte `uvicorn main:app` im web/api/-Verzeichnis." : msg });
    }
  }

  resetSession(): void {
    this._sessionId = null;
    this._answered = [];
    this._currentDocId = null;
    if (this._view) this._render("idle");
  }

  private _render(
    state: "idle" | "loading" | "result" | "error" | "no-editor" | "not-sdd" | "claude-missing",
    data?: {
      docId?: string;
      docType?: string;
      data?: AnalyzeResponse;
      answered?: AnsweredQuestion[];
      message?: string;
    }
  ): void {
    if (!this._view) return;
    this._view.webview.html = buildHtml(state, data);
  }
}

const SEV_ICON: Record<string, string> = {
  error: "🔴",
  warning: "🟡",
  suggestion: "💡",
};

function buildHtml(
  state: string,
  data?: {
    docId?: string;
    docType?: string;
    data?: AnalyzeResponse;
    answered?: AnsweredQuestion[];
    message?: string;
  }
): string {
  const css = `
    <style>
      body { font-family: var(--vscode-font-family); font-size: var(--vscode-font-size); color: var(--vscode-foreground); padding: 10px; }
      button { background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; padding: 5px 12px; cursor: pointer; border-radius: 2px; font-size: 12px; }
      button:hover { background: var(--vscode-button-hoverBackground); }
      button.secondary { background: var(--vscode-button-secondaryBackground); color: var(--vscode-button-secondaryForeground); }
      button.secondary:hover { background: var(--vscode-button-secondaryHoverBackground); }
      .muted { color: var(--vscode-descriptionForeground); font-size: 11px; }
      .card { border: 1px solid var(--vscode-panel-border); border-radius: 3px; padding: 8px 10px; margin-bottom: 8px; }
      .card.answered { opacity: 0.5; }
      .section-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--vscode-descriptionForeground); display: block; margin-bottom: 3px; }
      .q-text { font-size: 12px; margin: 3px 0 6px; }
      textarea { width: 100%; box-sizing: border-box; background: var(--vscode-input-background); color: var(--vscode-input-foreground); border: 1px solid var(--vscode-input-border); padding: 4px; font-size: 12px; font-family: inherit; resize: vertical; min-height: 50px; }
      .row { display: flex; gap: 6px; align-items: center; margin-top: 4px; }
      .group-label { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: var(--vscode-descriptionForeground); margin: 10px 0 5px; }
      .error-msg { color: var(--vscode-errorForeground); font-size: 12px; }
      .success { color: var(--vscode-testing-iconPassed); font-size: 12px; }
      h4 { margin: 0 0 8px; font-size: 13px; }
      .border-error { border-left: 3px solid var(--vscode-errorForeground); padding-left: 7px; }
      .border-warning { border-left: 3px solid var(--vscode-editorWarning-foreground); padding-left: 7px; }
      .border-suggestion { border-left: 3px solid var(--vscode-editorInfo-foreground); padding-left: 7px; }
    </style>
  `;

  const script = `
    <script>
      const vscode = acquireVsCodeApi();
      function analyze() { vscode.postMessage({ type: 'analyze' }); }
      function reanalyze() { vscode.postMessage({ type: 'reanalyze' }); }
      function openAnswer(id) {
        document.getElementById('ans-' + id).style.display = 'block';
        document.getElementById('btn-' + id).style.display = 'none';
      }
      function submitAnswer(id) {
        const answer = document.getElementById('txt-' + id).value;
        vscode.postMessage({ type: 'answer', id, answer });
        const card = document.getElementById('card-' + id);
        card.classList.add('answered');
        card.querySelector('.ans-area').innerHTML = '<span class="success">✓ Beantwortet' + (answer ? ': ' + answer : '') + '</span>';
      }
    </script>
  `;

  let body = "";

  if (state === "idle") {
    body = `
      <p class="muted">Öffne eine Spec- oder Contract-Datei und klicke Analysieren.</p>
      <button onclick="analyze()">🔍 Analysieren</button>
    `;
  } else if (state === "loading") {
    body = `
      <p class="muted">Analysiere ${data?.docId ?? "Dokument"}…</p>
    `;
  } else if (state === "no-editor") {
    body = `<p class="muted">Kein aktiver Editor. Öffne eine .md-Datei.</p>`;
  } else if (state === "not-sdd") {
    body = `<p class="muted">Diese Datei ist keine SDD-Spec oder -Contract (Dateiname muss mit SPEC- oder CON- beginnen).</p>
    <button onclick="analyze()">🔍 Trotzdem analysieren</button>`;
  } else if (state === "claude-missing") {
    body = `
      <p class="error-msg">⚠ Claude Code CLI nicht gefunden.</p>
      <p class="muted">Installiere Claude Code und melde dich an.</p>
    `;
  } else if (state === "error") {
    body = `
      <p class="error-msg">Fehler: ${escHtml(data?.message ?? "Unbekannter Fehler")}</p>
      <button class="secondary" onclick="analyze()">Erneut versuchen</button>
    `;
  } else if (state === "result" && data?.data) {
    const { questions, issues, suggestions } = data.data;
    const answered = data.answered ?? [];
    const openCount = questions.filter((q) => !answered.find((a) => a.id === q.id)).length;

    const isEmpty = questions.length === 0 && issues.length === 0 && suggestions.length === 0;

    let qHtml = "";
    if (questions.length > 0) {
      qHtml += `<p class="group-label">Nachfragen (${openCount} offen)</p>`;
      for (const q of questions) {
        const isAnswered = !!answered.find((a) => a.id === q.id);
        const ans = answered.find((a) => a.id === q.id);
        const borderClass = `border-${q.severity}`;
        const ansArea = isAnswered
          ? `<span class="success">✓ Beantwortet${ans?.answer ? ": " + escHtml(ans.answer) : ""}</span>`
          : `
            <button id="btn-${q.id}" style="font-size:11px;padding:2px 8px;" class="secondary" onclick="openAnswer('${q.id}')">Beantworten</button>
            <div id="ans-${q.id}" style="display:none">
              <textarea id="txt-${q.id}" placeholder="Deine Antwort (optional)…"></textarea>
              <div class="row">
                <button onclick="submitAnswer('${q.id}')" style="font-size:11px;padding:2px 8px;">Als beantwortet markieren</button>
                <button class="secondary" onclick="document.getElementById('ans-${q.id}').style.display='none';document.getElementById('btn-${q.id}').style.display='inline-block'" style="font-size:11px;padding:2px 8px;">Abbrechen</button>
              </div>
            </div>
          `;
        qHtml += `
          <div id="card-${q.id}" class="card ${borderClass}${isAnswered ? " answered" : ""}">
            ${q.section ? `<span class="section-label">${escHtml(q.section)}</span>` : ""}
            <p class="q-text">${SEV_ICON[q.severity] ?? "•"} ${escHtml(q.text)}</p>
            <div class="ans-area">${ansArea}</div>
          </div>
        `;
      }
    }

    let issHtml = "";
    if (issues.length > 0) {
      issHtml += `<p class="group-label">Probleme</p>`;
      for (const i of issues) {
        issHtml += `
          <div class="card border-${i.severity}">
            ${i.section ? `<span class="section-label">${escHtml(i.section)}</span>` : ""}
            <p class="q-text">${SEV_ICON[i.severity] ?? "•"} ${escHtml(i.text)}</p>
          </div>
        `;
      }
    }

    let sugHtml = "";
    if (suggestions.length > 0) {
      sugHtml += `<p class="group-label">Vorschläge</p>`;
      for (const s of suggestions) {
        sugHtml += `<div class="card border-suggestion"><p class="q-text">💡 ${escHtml(s.text)}</p></div>`;
      }
    }

    const statusLine = isEmpty
      ? `<p class="success">✓ Dokument sieht vollständig aus.</p>`
      : `<p class="muted">${escHtml(data.docId ?? "")} · ${openCount} offen</p>`;

    body = `
      <h4>🔍 KI-Analyse</h4>
      ${statusLine}
      ${qHtml}${issHtml}${sugHtml}
      <div class="row" style="margin-top:12px">
        <button onclick="reanalyze()">Erneut analysieren</button>
        ${answered.length > 0 ? `<span class="muted">(${answered.length} beantwortet)</span>` : ""}
      </div>
    `;
  }

  return `<!DOCTYPE html><html><head>${css}</head><body>${body}${script}</body></html>`;
}

function escHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
