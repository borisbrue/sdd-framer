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
exports.SddCodeLensProvider = void 0;
const vscode = __importStar(require("vscode"));
const frontmatter_1 = require("./frontmatter");
class SddCodeLensProvider {
    provideCodeLenses(document) {
        const fm = (0, frontmatter_1.parseFrontmatter)(document.fileName);
        if (!fm.id || !fm.id.startsWith("SPEC-")) {
            return [];
        }
        const contracts = fm.contracts?.length ?? 0;
        const tests = fm.tests?.length ?? 0;
        const issues = (contracts === 0 ? 1 : 0) + (tests === 0 ? 1 : 0);
        const issueLabel = issues > 0 ? ` · ⚠ ${issues} Lücken` : " · ✓";
        const lens = new vscode.CodeLens(new vscode.Range(0, 0, 0, 0), {
            title: `${contracts} contracts · ${tests} tests${issueLabel}`,
            command: "sdd.validate",
        });
        return [lens];
    }
}
exports.SddCodeLensProvider = SddCodeLensProvider;
//# sourceMappingURL=codelens.js.map