import * as vscode from "vscode";
import { execFile, spawn, ChildProcess } from "child_process";
import { resolveCliPath } from "./cli";

export type ServerStatus = "stopped" | "starting" | "running" | "error";

let _globalInstance: ServerManager | undefined;

export class ServerManager {
  private _proc: ChildProcess | undefined;
  private _port: number | null = null;
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

  getBaseUrl(): string | null {
    if (this._status === "running" && this._port) {
      return `http://localhost:${this._port}`;
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

    // sdd ui findet die web-API relativ zum installierten Paket (ui.py: parents[2]/web)
    // und setzt SDD_PROJECT_ROOT auf das Projektverzeichnis.
    // Das funktioniert für jedes Projekt das `sdd` installiert hat – nicht nur sdd-framer selbst.
    const sddBin = resolveCliPath();
    this._out.appendLine(`[SDD Server] sdd ui --project ${root} --port ${port} --no-browser`);

    const proc = spawn(sddBin, ["ui", "--project", root, "--port", String(port), "--no-browser"], {
      cwd: root,
    });
    this._proc = proc;

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error("Server-Start-Timeout nach 10 s"));
        this._setStatus("error");
      }, 10_000);

      const onData = (data: Buffer) => {
        const text = data.toString();
        this._out.append(text);
        // sdd ui prefixiert uvicorn-Zeilen mit "[api] " – daher beide Varianten prüfen
        const isReady =
          text.includes("Application startup complete") ||
          text.includes("Uvicorn running") ||
          text.includes("Server gestartet →");
        if (isReady) {
          clearTimeout(timer);
          this._port = port;
          this._setStatus("running");
          this._out.appendLine(`[SDD Server] Gestartet auf Port ${port}`);
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
    return `http://localhost:${_globalInstance.getPort()}`;
  }
  return vscode.workspace.getConfiguration("sdd").get<string>("webApiUrl", "http://localhost:8000");
}
