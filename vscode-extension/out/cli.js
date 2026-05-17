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
exports.resolveCliPath = resolveCliPath;
exports.runSdd = runSdd;
exports.findProjectRoot = findProjectRoot;
const vscode = __importStar(require("vscode"));
const child_process_1 = require("child_process");
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
function resolveCliPath() {
    const configured = vscode.workspace
        .getConfiguration("sdd")
        .get("cliPath", "");
    if (configured && fs.existsSync(configured)) {
        return configured;
    }
    // Suche in PATH-typischen Orten
    const candidates = [
        "/var/data/python/bin/sdd",
        "/usr/local/bin/sdd",
        "/usr/bin/sdd",
        path.join(process.env["HOME"] ?? "", ".local/bin/sdd"),
    ];
    for (const c of candidates) {
        if (fs.existsSync(c)) {
            return c;
        }
    }
    return "sdd"; // Fallback: aus PATH
}
function runSdd(args, cwd) {
    return new Promise((resolve, reject) => {
        const bin = resolveCliPath();
        (0, child_process_1.execFile)(bin, args, { cwd }, (err, stdout, stderr) => {
            if (err && err.code !== 1) {
                // exit 1 = Validierungsfehler (erwartet), alles andere ist ein echter Fehler
                reject(new Error(`sdd ${args[0]} fehlgeschlagen:\n${stderr || err.message}`));
            }
            else {
                resolve({ stdout, stderr });
            }
        });
    });
}
async function findProjectRoot(start) {
    let current = start;
    while (true) {
        if (fs.existsSync(path.join(current, ".sdd", "config.yaml"))) {
            return current;
        }
        const parent = path.dirname(current);
        if (parent === current) {
            return undefined;
        }
        current = parent;
    }
}
//# sourceMappingURL=cli.js.map