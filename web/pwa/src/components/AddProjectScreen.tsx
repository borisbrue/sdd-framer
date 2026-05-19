import { useState } from "react";
import { Project } from "../config";
import { CameraQrFlow, ManualQrFlow } from "../QrOnboardingFlow";
import QrScanner from "./QrScanner";

type Mode = "choose" | "scan" | "manual" | "rotating" | "error" | "cert";

interface Props {
  onAdded: (project: Project) => void;
  onCancel: () => void;
}

export default function AddProjectScreen({ onAdded, onCancel }: Props) {
  const [mode, setMode] = useState<Mode>("choose");
  const [errorMsg, setErrorMsg] = useState("");

  // Manuelles Formular
  const [url, setUrl] = useState("http://");
  const [token, setToken] = useState("");
  const [name, setName] = useState("");

  // Zertifikat-Onboarding — Hub-URL (Port 8000) vorausfüllen; Hub serviert /api/certs/root-ca
  // auf einem stabilen Port, dynamische Projektports werden bewusst ersetzt.
  function _defaultCertUrl(): string {
    const o = window.location.origin;
    if (o.includes("localhost") || o.includes("127.0.0.1")) return "";
    try {
      const u = new URL(o);
      u.port = "8000";
      return u.origin;
    } catch { return ""; }
  }
  const [certUrl, setCertUrl] = useState(_defaultCertUrl);

  async function handleQrDetected(rawJson: string) {
    setMode("rotating");
    try {
      const flow = new CameraQrFlow(rawJson, onAdded);
      await flow.execute();
    } catch (e: unknown) {
      setErrorMsg(e instanceof Error ? e.message : "Unbekannter Fehler");
      setMode("error");
    }
  }

  async function handleManualSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim() || !token.trim() || !name.trim()) return;
    setMode("rotating");
    try {
      const flow = new ManualQrFlow({ url: url.trim(), token: token.trim(), name: name.trim() }, onAdded);
      await flow.execute();
    } catch (e: unknown) {
      setErrorMsg(e instanceof Error ? e.message : "Unbekannter Fehler");
      setMode("error");
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <button onClick={onCancel} style={styles.backBtn}>←</button>
        <span style={styles.title}>Projekt hinzufügen</span>
      </div>

      {mode === "choose" && (
        <div style={styles.body}>
          <p style={{ color: "var(--muted)", marginBottom: 24, fontSize: 14 }}>
            Verbinde ein SDD-Backend indem du den QR-Code im Web UI scannst,
            oder gib die Verbindungsdaten manuell ein.
          </p>
          <button className="primary" onClick={() => setMode("scan")} style={styles.bigBtn}>
            📷 QR-Code scannen
          </button>
          <button onClick={() => setMode("manual")} style={{ ...styles.bigBtn, marginTop: 12 }}>
            ✎ Manuell eingeben
          </button>
          <div style={{ marginTop: 28, borderTop: "1px solid var(--border)", paddingTop: 20 }}>
            <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 12 }}>
              Erstes Mal auf diesem Gerät? Installiere zuerst das Zertifikat damit HTTPS funktioniert.
            </p>
            <button onClick={() => setMode("cert")} style={{ ...styles.bigBtn, fontSize: 13 }}>
              🔐 Zertifikat installieren
            </button>
          </div>
        </div>
      )}

      {mode === "scan" && (
        <div style={styles.body}>
          <p style={{ color: "var(--muted)", marginBottom: 16, fontSize: 13, textAlign: "center" }}>
            Halte die Kamera auf den QR-Code im SDD Web UI.
          </p>
          <QrScanner
            onDetected={handleQrDetected}
            onError={(msg) => { setErrorMsg(msg); setMode("error"); }}
          />
          <button onClick={() => setMode("choose")} style={{ marginTop: 16, width: "100%" }}>
            Abbrechen
          </button>
        </div>
      )}

      {mode === "manual" && (
        <div style={styles.body}>
          <form onSubmit={handleManualSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <label style={styles.fieldLabel}>
              Projektname
              <input
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="sdd-framer"
                required
                style={styles.input}
              />
            </label>
            <label style={styles.fieldLabel}>
              Server-URL
              <input
                value={url}
                onChange={e => setUrl(e.target.value)}
                placeholder="http://rechner.tail.ts.net:8000"
                type="url"
                required
                style={styles.input}
              />
            </label>
            <label style={styles.fieldLabel}>
              Bearer-Token
              <input
                value={token}
                onChange={e => setToken(e.target.value)}
                placeholder="a1b2c3…"
                required
                style={styles.input}
              />
            </label>
            <p style={{ fontSize: 11, color: "var(--muted)", margin: 0 }}>
              Der Token wird sofort durch einen neuen ersetzt.
            </p>
            <button type="submit" className="primary">Verbinden</button>
            <button type="button" onClick={() => setMode("choose")}>Zurück</button>
          </form>
        </div>
      )}

      {mode === "cert" && (
        <div style={styles.body}>
          <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 20, lineHeight: 1.6 }}>
            Gib die URL deines SDD-Servers ein (Hub oder Projektserver). Safari öffnet das
            Zertifikat und bietet die Installation an.
          </p>
          <label style={styles.fieldLabel}>
            Server-URL
            <input
              value={certUrl}
              onChange={e => setCertUrl(e.target.value)}
              placeholder="https://192.168.0.100:8000"
              type="url"
              style={styles.input}
              autoCapitalize="none"
            />
          </label>
          <a
            href={certUrl ? `${certUrl.replace(/\/$/, "")}/api/certs/root-ca` : "#"}
            onClick={e => { if (!certUrl) e.preventDefault(); }}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "block",
              marginTop: 16,
              padding: "12px 0",
              textAlign: "center",
              background: certUrl ? "var(--accent)" : "var(--surface-2, #21262d)",
              color: certUrl ? "#fff" : "var(--muted)",
              borderRadius: 8,
              textDecoration: "none",
              fontWeight: 600,
              fontSize: 15,
              pointerEvents: certUrl ? "auto" : "none",
            }}
          >
            Zertifikat laden
          </a>
          <div style={{
            marginTop: 20, background: "var(--surface-2, #161b22)",
            borderRadius: 8, padding: 14, fontSize: 12,
            color: "var(--muted)", lineHeight: 1.7,
          }}>
            <strong style={{ color: "var(--text)" }}>Nach dem Download (iOS):</strong><br />
            Einstellungen → Allgemein → VPN &amp; Geräteverwaltung → Profil installieren<br />
            Dann: Einstellungen → Allgemein → Info → Zertifikatsvertrauenseinstellungen →
            <strong style={{ color: "var(--text)" }}> mkcert aktivieren</strong>
          </div>
          <button onClick={() => setMode("choose")} style={{ marginTop: 16, width: "100%" }}>
            Zurück
          </button>
        </div>
      )}

      {mode === "rotating" && (
        <div style={{ ...styles.body, alignItems: "center", justifyContent: "center" }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>⟳</div>
          <p style={{ color: "var(--muted)" }}>Token wird rotiert…</p>
        </div>
      )}

      {mode === "error" && (
        <div style={styles.body}>
          <div style={{
            background: "var(--surface)", border: "1px solid var(--red)",
            borderRadius: 8, padding: 16, marginBottom: 20,
          }}>
            <div style={{ color: "var(--red)", fontWeight: 600, marginBottom: 6 }}>Fehler</div>
            <div style={{ fontSize: 13, color: "var(--text)" }}>{errorMsg}</div>
          </div>
          <button onClick={() => setMode("choose")} style={{ width: "100%" }}>Nochmal versuchen</button>
          <button onClick={onCancel} style={{ width: "100%", marginTop: 8 }}>Abbrechen</button>
        </div>
      )}
    </div>
  );
}

const styles = {
  container: { display: "flex", flexDirection: "column" as const, height: "100%", background: "var(--bg)" },
  header: {
    display: "flex", alignItems: "center", gap: 12,
    padding: "14px 16px",
    paddingTop: "calc(14px + env(safe-area-inset-top))",
    borderBottom: "1px solid var(--border)",
    background: "var(--surface)",
  },
  backBtn: { background: "transparent", border: "none", color: "var(--accent)", fontSize: 20, cursor: "pointer", padding: 0 },
  title: { fontWeight: 700, fontSize: 16, color: "var(--text)" },
  body: { flex: 1, padding: 20, display: "flex", flexDirection: "column" as const, overflowY: "auto" as const },
  bigBtn: { width: "100%", padding: "14px 0", fontSize: 15, fontWeight: 600 },
  fieldLabel: { display: "flex", flexDirection: "column" as const, gap: 6, fontSize: 13, color: "var(--muted)" },
  input: {
    padding: "10px 12px",
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: 6,
    color: "var(--text)",
    fontSize: 14,
    width: "100%",
    boxSizing: "border-box" as const,
  },
};
