/**
 * QrOnboardingFlow — Template Method Pattern (SPEC-0025 §3.4)
 *
 * Definiert die unveränderliche Sequenz des Onboarding-Flows (CON-0087 G-01):
 *   scan → validate → rotateToken → saveProject → navigate
 *
 * Der `scan`-Schritt ist der einzige variable Teil — CameraQrFlow und ManualQrFlow
 * überschreiben ihn. Alle anderen Schritte sind fix und können nicht übersprungen werden.
 */
import { Project, ProjectRegistry, generateId } from "./config";

export interface QrData {
  sdd: number;
  name: string;
  url: string;
  token: string;
  hub?: string;
  root?: string;
}

export abstract class QrOnboardingFlow {
  /** Template Method — unveränderliche Sequenz */
  async execute(): Promise<Project> {
    // Stellt sicher dass sdd_projects existiert bevor wir schreiben (CON-0087 G-07)
    ProjectRegistry.init();

    const raw = await this.scan();
    const data = this.validate(raw);
    const newToken = await this.rotateToken(data);
    const project = this.saveProject(data, newToken);
    this.navigate(project);
    return project;
  }

  /** ABSTRAKT: überschreibbar durch Kamera-Flow oder manuelles Formular */
  protected abstract scan(): Promise<string>;

  /** ABSTRAKT: Navigation nach erfolgreichem Onboarding */
  protected abstract navigate(project: Project): void;

  /** Validiert das QR-JSON. Wirft bei fehlenden Pflichtfeldern (CON-0087 G-03). */
  protected validate(raw: string): QrData {
    let data: unknown;
    try {
      data = JSON.parse(raw);
    } catch {
      throw new Error("Ungültiger QR-Code – kein gültiges JSON");
    }
    if (typeof data !== "object" || data === null) {
      throw new Error("Ungültiger QR-Code – kein Objekt");
    }
    const d = data as Record<string, unknown>;
    if (!d.url || !d.token || !d.name) {
      throw new Error("Ungültiger QR-Code – SDD-Felder fehlen");
    }
    return {
      sdd: typeof d.sdd === "number" ? d.sdd : 1,
      name: String(d.name),
      url: String(d.url).replace(/\/$/, ""),
      token: String(d.token),
      hub: d.hub ? String(d.hub).replace(/\/$/, "") : undefined,
      root: d.root ? String(d.root) : undefined,
    };
  }

  /**
   * POST /api/auth/rotate-token — gibt den neuen Token zurück.
   * Wirft bei Netzwerkfehler oder 401 (CON-0087 G-02).
   */
  protected async rotateToken(data: QrData): Promise<string> {
    let response: Response;
    try {
      response = await fetch(`${data.url}/api/auth/rotate-token`, {
        method: "POST",
        headers: { Authorization: `Bearer ${data.token}` },
      });
    } catch (e: unknown) {
      const detail = e instanceof Error ? e.message : String(e);
      throw new Error(`Server nicht erreichbar (${detail})`);
    }

    if (response.status === 401) {
      throw new Error("Token ungültig – QR-Code wurde bereits verwendet");
    }
    if (!response.ok) {
      throw new Error(`Server-Fehler (${response.status}) – Projekt nicht gespeichert`);
    }

    const body = await response.json() as { token?: string };
    if (!body.token) {
      throw new Error("Ungültige Server-Antwort – kein Token erhalten");
    }
    return body.token;
  }

  /**
   * Speichert das Projekt mit dem NEUEN Token in sdd_projects[].
   * Wird erst nach erfolgreichem rotateToken aufgerufen (CON-0087 INV-01/INV-02).
   * QR `url` → Schema `baseUrl` (CON-0087 G-03 Mapping).
   */
  protected saveProject(data: QrData, newToken: string): Project {
    const project: Project = {
      id: generateId(),
      name: data.name,
      baseUrl: data.url,  // QR url → baseUrl (CON-0087 G-03)
      token: newToken,
      addedAt: new Date().toISOString(),
      hubUrl: data.hub,
      projectRoot: data.root,
    };
    ProjectRegistry.add(project);
    ProjectRegistry.setActive(project.id);
    return project;
  }
}

/** Kamera-basierter Flow: Raw-JSON kommt vom QR-Scanner */
export class CameraQrFlow extends QrOnboardingFlow {
  constructor(
    private readonly rawJson: string,
    private readonly onDone: (project: Project) => void,
  ) {
    super();
  }

  protected async scan(): Promise<string> {
    return this.rawJson;
  }

  protected navigate(project: Project): void {
    this.onDone(project);
  }
}

/** Manueller Flow: JSON wird aus Formularfeldern zusammengebaut */
export class ManualQrFlow extends QrOnboardingFlow {
  constructor(
    private readonly formData: { url: string; token: string; name: string },
    private readonly onDone: (project: Project) => void,
  ) {
    super();
  }

  protected async scan(): Promise<string> {
    return JSON.stringify({
      sdd: 1,
      name: this.formData.name,
      url: this.formData.url,
      token: this.formData.token,
    });
  }

  protected navigate(project: Project): void {
    this.onDone(project);
  }
}
