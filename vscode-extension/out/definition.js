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
exports.SddHoverProvider = exports.SddDefinitionProvider = void 0;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const ID_RE = /\b(SPEC|CON|TST|ADR)-\d{4}\b/g;
function findFileById(id, rootDirs) {
    const prefix = id.split("-")[0];
    const subdirs = {
        SPEC: ["specs"],
        CON: ["contracts", "contracts/api", "contracts/behavior", "contracts/data", "contracts/performance"],
        TST: ["tests", "tests/unit", "tests/contract", "tests/acceptance", "tests/performance", "tests/property"],
        ADR: ["docs/adr"],
    };
    const searchDirs = subdirs[prefix] ?? [];
    for (const root of rootDirs) {
        for (const sub of searchDirs) {
            const dir = path.join(root, sub);
            if (!fs.existsSync(dir)) {
                continue;
            }
            const match = fs.readdirSync(dir).find((f) => f.startsWith(id) && f.endsWith(".md"));
            if (match) {
                return path.join(dir, match);
            }
        }
    }
    return undefined;
}
class SddDefinitionProvider {
    constructor(projectRoot) {
        this.projectRoot = projectRoot;
    }
    provideDefinition(document, position) {
        const line = document.lineAt(position.line).text;
        let match;
        ID_RE.lastIndex = 0;
        while ((match = ID_RE.exec(line)) !== null) {
            const start = match.index;
            const end = start + match[0].length;
            if (position.character >= start && position.character <= end) {
                const id = match[0];
                const filePath = findFileById(id, [this.projectRoot]);
                if (filePath) {
                    return new vscode.Location(vscode.Uri.file(filePath), new vscode.Position(0, 0));
                }
            }
        }
        return undefined;
    }
}
exports.SddDefinitionProvider = SddDefinitionProvider;
class SddHoverProvider {
    constructor(projectRoot) {
        this.projectRoot = projectRoot;
    }
    provideHover(document, position) {
        const line = document.lineAt(position.line).text;
        let match;
        ID_RE.lastIndex = 0;
        while ((match = ID_RE.exec(line)) !== null) {
            const start = match.index;
            const end = start + match[0].length;
            if (position.character >= start && position.character <= end) {
                const id = match[0];
                const filePath = findFileById(id, [this.projectRoot]);
                if (filePath) {
                    try {
                        const text = fs.readFileSync(filePath, "utf8");
                        const titleMatch = /^title:\s*"?(.+?)"?\s*$/m.exec(text);
                        const statusMatch = /^status:\s*(\S+)/m.exec(text);
                        const title = titleMatch ? titleMatch[1] : "(kein Titel)";
                        const status = statusMatch ? statusMatch[1] : "?";
                        return new vscode.Hover(new vscode.MarkdownString(`**${id}** – ${title}\n\nStatus: \`${status}\``));
                    }
                    catch {
                        return undefined;
                    }
                }
            }
        }
        return undefined;
    }
}
exports.SddHoverProvider = SddHoverProvider;
//# sourceMappingURL=definition.js.map