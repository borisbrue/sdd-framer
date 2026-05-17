import * as vscode from "vscode";
import { execFile } from "child_process";
import * as path from "path";
import * as fs from "fs";

export function resolveCliPath(): string {
  const configured = vscode.workspace
    .getConfiguration("sdd")
    .get<string>("cliPath", "");
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

export function runSdd(
  args: string[],
  cwd: string
): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    const bin = resolveCliPath();
    execFile(bin, args, { cwd }, (err, stdout, stderr) => {
      if (err && err.code !== 1) {
        // exit 1 = Validierungsfehler (erwartet), alles andere ist ein echter Fehler
        reject(new Error(`sdd ${args[0]} fehlgeschlagen:\n${stderr || err.message}`));
      } else {
        resolve({ stdout, stderr });
      }
    });
  });
}

export async function findProjectRoot(start: string): Promise<string | undefined> {
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
