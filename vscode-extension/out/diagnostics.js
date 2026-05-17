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
exports.createDiagnosticCollection = createDiagnosticCollection;
exports.runValidation = runValidation;
const vscode = __importStar(require("vscode"));
const cli_1 = require("./cli");
const COLLECTION_NAME = "sdd";
function createDiagnosticCollection() {
    return vscode.languages.createDiagnosticCollection(COLLECTION_NAME);
}
async function runValidation(projectRoot, collection) {
    collection.clear();
    let issues = [];
    try {
        const result = await (0, cli_1.runSdd)(["validate", "--instruct"], projectRoot);
        const parsed = JSON.parse(result.stdout);
        issues = parsed.issues ?? [];
    }
    catch {
        return;
    }
    const byFile = new Map();
    for (const issue of issues) {
        const absPath = vscode.Uri.file(`${projectRoot}/${issue.file}`);
        const severity = issue.severity === "error"
            ? vscode.DiagnosticSeverity.Error
            : vscode.DiagnosticSeverity.Warning;
        const message = issue.instruction
            ? `${issue.message}\n→ ${issue.instruction}`
            : issue.message;
        const diag = new vscode.Diagnostic(new vscode.Range(0, 0, 0, 0), message, severity);
        diag.source = "sdd";
        const key = absPath.toString();
        if (!byFile.has(key)) {
            byFile.set(key, []);
        }
        byFile.get(key).push(diag);
    }
    for (const [uri, diags] of byFile) {
        collection.set(vscode.Uri.parse(uri), diags);
    }
}
//# sourceMappingURL=diagnostics.js.map