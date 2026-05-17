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
exports.parseFrontmatter = parseFrontmatter;
const fs = __importStar(require("fs"));
const FM_RE = /^---\s*\n([\s\S]*?)\n---\s*\n/;
function parseFrontmatter(filePath) {
    try {
        const text = fs.readFileSync(filePath, "utf8");
        const m = FM_RE.exec(text);
        if (!m) {
            return {};
        }
        // Minimaler YAML-Parser für flache Key-Value-Paare und Listen
        return parseYamlLite(m[1]);
    }
    catch {
        return {};
    }
}
function parseYamlLite(yaml) {
    const result = {};
    const lines = yaml.split("\n");
    let currentKey = null;
    let inList = false;
    for (const raw of lines) {
        const line = raw.replace(/#.*$/, "").trimEnd(); // Kommentare entfernen
        // Listenelement
        const listMatch = /^(\s+)-\s+(.+)$/.exec(line);
        if (listMatch && inList && currentKey) {
            const val = listMatch[2].trim().replace(/^["']|["']$/g, "");
            result[currentKey].push(val);
            continue;
        }
        // Key: Value
        const kvMatch = /^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$/.exec(line);
        if (kvMatch) {
            currentKey = kvMatch[1];
            const raw_val = kvMatch[2].trim();
            if (raw_val === "" || raw_val === "[]") {
                result[currentKey] = raw_val === "[]" ? [] : undefined;
                inList = raw_val === "";
            }
            else if (raw_val.startsWith("[")) {
                // Inline-Liste: [CON-0001, CON-0002]
                result[currentKey] = raw_val
                    .replace(/^\[|\]$/g, "")
                    .split(",")
                    .map((s) => s.trim().replace(/^["']|["']$/g, ""))
                    .filter(Boolean);
                inList = false;
            }
            else {
                result[currentKey] = raw_val.replace(/^["']|["']$/g, "");
                inList = false;
            }
        }
    }
    return result;
}
//# sourceMappingURL=frontmatter.js.map