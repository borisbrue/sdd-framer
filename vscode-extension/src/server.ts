import * as vscode from "vscode";
import * as http from "http";
import * as path from "path";
import * as fs from "fs";
import { execFile, spawn, ChildProcess } from "child_process";
import { resolveCliPath } from "./cli";

export type ServerStatus = "stopped" | "starting" | "running" | "error";

let _globalInstance: ServerManager | undefined;

export class ServerManager {
  private _proc: ChildProcess | undefined;
  private _port: number | null = null;
  private _root: string | null = null;
  private _detectedScheme: "http" | "https" | null = null;
  private _status: ServerStatus = "stopped";
  private readonly _onDidChangeStatus = new vscode.EventEmitter<ServerStatus>();
  readonly onDidChangeStatus = this._onDidChangeStatus.event;

  private constructor(private readonly _out: vscode.OutputChannel) {}

  static getInstance(out: vscode.OutputChannel): ServerManager {
    if (!_globalInstance) {
      _globalInstance = new ServerManager(out);
    }
    return _globalInstance;
  }

  getPort(): number | null {
    return this._port;
  }

  getStatus(): ServerStatus {
    return this._status;
  }

  private _hasCert(): boolean {
    if (!this._root) { return false; }
    return fs.existsSync(path.join(this._root, ".certs", "cert.pem"));
  }

  getBaseUrl(): string | null {
    if (this._status === "running" && this._port) {
      const scheme = this._detectedScheme ?? (this._hasCert() ? "https" : "http");
      return `${scheme}://localhost:${this._port}`;
    }
    return null;
  }

  async start(root: string): Promise<void> {
    if (this._status === "running" || this._status === "starting") {
      return;
    }
    this._setStatus("starting");

    let port: number;
    try {
      const configured = vscode.workspace.getConfiguration("sdd").get<number>("webUi.port", 0);
      port = configured > 0 ? configured : await this._getFreePort(root);
    } catch {
      port = 8000;
    }

    this._root = root;

    const sddBin = resolveCliPath();
    const externalUrl = vscode.workspace.getConfiguration("sdd").get<string>("webUi.externalUrl", "");
    const spawnArgs = ["ui", "--project", root, "--port", String(port), "--no-browser"];
    if (externalUrl) {
      spawnArgs.push("--external-url", externalUrl);
    }
    this._out.appendLine(`[SDD Server] sdd ${spawnArgs.join(" ")}`);
    this._out.appendLine(`[SDD Server] HTTPS: ${this._hasCert()}`);

    const proc = spawn(sddBin, spawnArgs, { cwd: root });
    this._proc = proc;

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error("Server-Start-Timeout nach 30 s"));
        this._setStatus("error");
      }, 30_000);

      const onData = (data: Buffer) => {
        const text = data.toString();
        this._out.append(text);
        // Schema direkt aus Uvicorn-Output lesen: "Uvicorn running on https://..."
        const uvicornMatch = text.match(/Uvicorn running on (https?):/);
        if (uvicornMatch) {
          this._detectedScheme = uvicornMatch[1] as "http" | "https";
        }
        const isReady =
          text.includes("Application startup complete") ||
          text.includes("Uvicorn running on");
        if (isReady) {
          clearTimeout(timer);
          this._port = port;
          this._setStatus("running");
          const scheme = this._detectedScheme ?? (this._hasCert() ? "https" : "http");
          this._out.appendLine(`[SDD Server] Gestartet auf Port ${port} (${scheme})`);
          this._hubPost("/api/hub/register", { port, name: path.basename(root), root, scheme });
          resolve();
        }
      };

      proc.stdout?.on("data", onData);
      proc.stderr?.on("data", onData); // uvicorn logs to stderr

      proc.once("exit", (code) => {
        clearTimeout(timer);
        this._proc = undefined;
        this._port = null;
        if (this._status !== "stopped") {
          this._setStatus(code === 0 ? "stopped" : "error");
        }
        reject(new Error(`Prozess beendet mit Code ${code}`));
      });

      proc.once("error", (err) => {
        clearTimeout(timer);
        this._setStatus("error");
        reject(err);
      });
    });
  }

  async stop(): Promise<void> {
    const proc = this._proc;
    if (!proc) {
      this._setStatus("stopped");
      return;
    }
    return new Promise((resolve) => {
      const fallback = setTimeout(() => {
        proc.kill("SIGKILL");
        this._proc = undefined;
        this._port = null;
        this._setStatus("stopped");
        resolve();
      }, 3_000);

      proc.once("exit", () => {
        clearTimeout(fallback);
        this._proc = undefined;
        this._port = null;
        this._setStatus("stopped");
        resolve();
      });

      if (this._port) {
        this._hubPost("/api/hub/deregister", { port: this._port });
      }
      proc.kill("SIGTERM");
    });
  }

  dispose(): void {
    this.stop();
    this._onDidChangeStatus.dispose();
    _globalInstance = undefined;
  }

  private _setStatus(s: ServerStatus): void {
    this._status = s;
    this._onDidChangeStatus.fire(s);
  }

  private _hubPost(endpoint: string, body: object): void {
    const data = JSON.stringify(body);
    const hubPort = vscode.workspace.getConfiguration("sdd").get<number>("hub.port", 8000);
    const req = http.request({
      hostname: "localhost",
      port: hubPort,
      path: endpoint,
      method: "POST",
      headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(data) },
    });
    req.on("error", () => {});
    req.write(data);
    req.end();
  }

  private _python(): string {
    return vscode.workspace.getConfiguration("sdd").get<string>("pythonPath", "python");
  }

  private _getFreePort(root: string): Promise<number> {
    return new Promise((resolve) => {
      execFile(
        this._python(),
        ["-c", "import socket; s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1]); s.close()"],
        { cwd: root },
        (err, stdout) => {
          if (err) {
            resolve(8000);
          } else {
            resolve(parseInt(stdout.trim(), 10) || 8000);
          }
        }
      );
    });
  }
}

export function getServerUrl(): string {
  if (_globalInstance?.getStatus() === "running" && _globalInstance.getPort()) {
    return _globalInstance.getBaseUrl()!;
  }
  return vscode.workspace.getConfiguration("sdd").get<string>("webApiUrl", "http://localhost:8000");
}
