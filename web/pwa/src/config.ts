/**
 * ProjectRegistry — Composite Pattern (SPEC-0025 §3.4)
 *
 * Kapselt alle localStorage-Operationen für die Multi-Projekt-Liste.
 * Consumer sprechen ausschliesslich mit dieser Klasse, nie direkt mit localStorage.
 */

export interface Project {
  id: string;
  name: string;
  baseUrl: string;
  token: string;
  addedAt: string;
  /** Stabiler Pfad des Projekts auf dem Server – Hub-Matching-Key */
  projectRoot?: string;
  /** URL des Hub-Servers für automatische Port-Aktualisierung */
  hubUrl?: string;
  /** Gesetzt wenn ein API-Call 401 zurückgab — zeigt Re-Auth-Banner (CON-0087 G-06) */
  auth_required?: boolean;
}

/** UUID v4 — works in both secure (HTTPS) and non-secure (HTTP) contexts. */
export function generateId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === "x" ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

const PROJECTS_KEY = "sdd_projects";
const ACTIVE_KEY = "sdd_active_project";
const LEGACY_KEY = "sdd_config"; // SPEC-0024 → SPEC-0025 Migration (CON-0088)

export const ProjectRegistry = {
  /**
   * Initialisierung beim App-Start:
   * 1. Migriert sdd_config (SPEC-0024) zu sdd_projects[] (SPEC-0025)
   * 2. Stellt sicher dass sdd_projects ein valides Array ist (CON-0088 INV-01)
   */
  init(): void {
    const legacy = localStorage.getItem(LEGACY_KEY);
    if (legacy) {
      try {
        const old = JSON.parse(legacy) as Record<string, string>;
        const project: Project = {
          id: generateId(),
          name: "Mein SDD-Projekt",
          baseUrl: (old.baseUrl ?? old.base_url ?? "").replace(/\/$/, ""),
          token: old.token ?? "",
          addedAt: new Date().toISOString(),
        };
        _save([project]);
        localStorage.setItem(ACTIVE_KEY, project.id);
        localStorage.removeItem(LEGACY_KEY);
      } catch {
        // korrupter Legacy-Eintrag — ignorieren
        localStorage.removeItem(LEGACY_KEY);
      }
    }
    if (!localStorage.getItem(PROJECTS_KEY)) {
      _save([]);
    }
  },

  getAll(): Project[] {
    try {
      const raw = localStorage.getItem(PROJECTS_KEY);
      const parsed = JSON.parse(raw ?? "[]");
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  },

  add(project: Project): void {
    const projects = this.getAll();
    projects.push(project);
    _save(projects);
  },

  update(id: string, patch: Partial<Project>): void {
    const projects = this.getAll().map(p => p.id === id ? { ...p, ...patch } : p);
    _save(projects);
  },

  remove(id: string): void {
    const projects = this.getAll().filter(p => p.id !== id);
    _save(projects);
    if (this.getActiveId() === id) {
      // Nächstes Projekt aktivieren, oder null wenn Liste leer
      const next = projects[0]?.id ?? null;
      localStorage.setItem(ACTIVE_KEY, next ?? "");
    }
  },

  setActive(id: string): void {
    localStorage.setItem(ACTIVE_KEY, id);
  },

  getActiveId(): string | null {
    return localStorage.getItem(ACTIVE_KEY) || null;
  },

  /** Gibt das aktive Projekt zurück, oder null wenn keins gesetzt (CON-0088 INV-02) */
  getActive(): Project | null {
    const id = this.getActiveId();
    if (!id) return null;
    return this.getAll().find(p => p.id === id) ?? null;
  },
};

function _save(projects: Project[]): void {
  localStorage.setItem(PROJECTS_KEY, JSON.stringify(projects));
}

interface _HubEntry {
  root: string;
  name: string;
  externalUrl: string;
  status: string;
}

/**
 * Fragt alle bekannten Hub-URLs ab und aktualisiert baseUrl für Projekte
 * deren Port sich geändert hat (z.B. nach Server-Neustart).
 * Gibt die aktualisierte Projektliste zurück und persistiert sie.
 */
export async function refreshProjectsFromHub(projects: Project[]): Promise<Project[]> {
  const hubUrls = [...new Set(projects.map(p => p.hubUrl).filter(Boolean))] as string[];
  if (hubUrls.length === 0) return projects;

  let updated = [...projects];
  let changed = false;

  for (const hubUrl of hubUrls) {
    try {
      const res = await fetch(`${hubUrl}/api/hub/projects`, { signal: AbortSignal.timeout(3000) });
      if (!res.ok) continue;
      const hubEntries = await res.json() as _HubEntry[];

      for (const entry of hubEntries) {
        if (entry.status !== "online" || !entry.externalUrl) continue;
        const idx = updated.findIndex(p =>
          (p.projectRoot && p.projectRoot === entry.root) || p.name === entry.name
        );
        if (idx >= 0 && updated[idx].baseUrl !== entry.externalUrl) {
          updated[idx] = { ...updated[idx], baseUrl: entry.externalUrl };
          changed = true;
        }
      }
    } catch {
      // Hub nicht erreichbar – still ignorieren
    }
  }

  if (changed) _save(updated);
  return updated;
}
