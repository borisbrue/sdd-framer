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
exports.ServerManager = void 0;
exports.getServerUrl = getServerUrl;
const vscode = __importStar(require("vscode"));
const http = __importStar(require("http"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const child_process_1 = require("child_process");
const cli_1 = require("./cli");
let _globalInstance;
class ServerManager {
    constructor(_out) {
        this._out = _out;
        this._port = null;
        this._root = null;
        this._detectedScheme = null;
        this._status = "stopped";
        this._onDidChangeStatus = new vscode.EventEmitter();
        this.onDidChangeStatus = this._onDidChangeStatus.event;
    }
    static getInstance(out) {
        if (!_globalInstance) {
            _globalInstance = new ServerManager(out);
        }
        return _globalInstance;
    }
    getPort() {
        return this._port;
    }
    getStatus() {
        return this._status;
    }
    _hasCert() {
        if (!this._root) {
            return false;
        }
        return fs.existsSync(path.join(this._root, ".certs", "cert.pem"));
    }
    getBaseUrl() {
        if (this._status === "running" && this._port) {
            const scheme = this._detectedScheme ?? (this._hasCert() ? "https" : "http");
            return `${scheme}://localhost:${this._port}`;
        }
        return null;
    }
    async start(root) {
        if (this._status === "running" || this._status === "starting") {
            return;
        }
        this._setStatus("starting");
        let port;
        try {
            const configured = vscode.workspace.getConfiguration("sdd").get("webUi.port", 0);
            port = configured > 0 ? configured : await this._getFreePort(root);
        }
        catch {
            port = 8000;
        }
        this._root = root;
        const sddBin = (0, cli_1.resolveCliPath)();
        const externalUrl = vscode.workspace.getConfiguration("sdd").get("webUi.externalUrl", "");
        const spawnArgs = ["ui", "--project", root, "--port", String(port), "--no-browser"];
        if (externalUrl) {
            spawnArgs.push("--external-url", externalUrl);
        }
        this._out.appendLine(`[SDD Server] sdd ${spawnArgs.join(" ")}`);
        this._out.appendLine(`[SDD Server] HTTPS: ${this._hasCert()}`);
        const proc = (0, child_process_1.spawn)(sddBin, spawnArgs, { cwd: root });
        this._proc = proc;
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                reject(new Error("Server-Start-Timeout nach 30 s"));
                this._setStatus("error");
            }, 30000);
            const onData = (data) => {
                const text = data.toString();
                this._out.append(text);
                // Schema direkt aus Uvicorn-Output lesen: "Uvicorn running on https://..."
                const uvicornMatch = text.match(/Uvicorn running on (https?):/);
                if (uvicornMatch) {
                    this._detectedScheme = uvicornMatch[1];
                }
                const isReady = text.includes("Application startup complete") ||
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
    async stop() {
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
            }, 3000);
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
    dispose() {
        this.stop();
        this._onDidChangeStatus.dispose();
        _globalInstance = undefined;
    }
    _setStatus(s) {
        this._status = s;
        this._onDidChangeStatus.fire(s);
    }
    _hubPost(endpoint, body) {
        const data = JSON.stringify(body);
        const hubPort = vscode.workspace.getConfiguration("sdd").get("hub.port", 8000);
        const req = http.request({
            hostname: "localhost",
            port: hubPort,
            path: endpoint,
            method: "POST",
            headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(data) },
        });
        req.on("error", () => { });
        req.write(data);
        req.end();
    }
    _python() {
        return vscode.workspace.getConfiguration("sdd").get("pythonPath", "python");
    }
    _getFreePort(root) {
        return new Promise((resolve) => {
            (0, child_process_1.execFile)(this._python(), ["-c", "import socket; s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1]); s.close()"], { cwd: root }, (err, stdout) => {
                if (err) {
                    resolve(8000);
                }
                else {
                    resolve(parseInt(stdout.trim(), 10) || 8000);
                }
            });
        });
    }
}
exports.ServerManager = ServerManager;
function getServerUrl() {
    if (_globalInstance?.getStatus() === "running" && _globalInstance.getPort()) {
        return _globalInstance.getBaseUrl();
    }
    return vscode.workspace.getConfiguration("sdd").get("webApiUrl", "http://localhost:8000");
}
//# sourceMappingURL=server.js.map