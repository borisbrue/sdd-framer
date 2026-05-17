import { useEffect, useState } from "react";
import { api, QrPayload, ServerInfo } from "../api";
import QrCodeOverlay from "./QrCodeOverlay";

interface Props {
  onClose: () => void;
}

export default function ServerInfoPanel({ onClose }: Props) {
  const [info, setInfo] = useState<ServerInfo | null>(null);
  const [qrPayload, setQrPayload] = useState<QrPayload | null>(null);
  const [loadingQr, setLoadingQr] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.serverInfo()
      .then(setInfo)
      .catch(() => setError("Server-Info konnte nicht geladen werden."));
  }, []);

  async function handleShowQr() {
    setLoadingQr(true);
    setError("");
    try {
      const payload = await api.qrPayload();
      setQrPayload(payload);
    } catch (e: unknown) {
      if (e instanceof Error && e.message === "no_token_configured") {
        setError("Kein Token konfiguriert. Starte mit --external-url und füge pwa.auth.token zu config.yaml hinzu.");
      } else if (e instanceof Error && e.message === "no_external_url_configured") {
        setError("Keine externe URL gesetzt. Starte den Server mit --external-url <url>.");
      } else {
        setError("QR-Code konnte nicht generiert werden.");
      }
    } finally {
      setLoadingQr(false);
    }
  }

  return (
    <>
      <div style={{
        position: "fixed", inset: 0,
        background: "rgba(0,0,0,0.5)",
        display: "flex", alignItems: "flex-start", justifyContent: "flex-end",
        zIndex: 900,
        paddingTop: 52, paddingRight: 12,
      }} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
        <div style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 10,
          padding: 20,
          minWidth: 280,
          maxWidth: 360,
          display: "flex", flexDirection: "column", gap: 14,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontWeight: 700, color: "var(--accent)", fontSize: 14 }}>Server-Info</span>
            <button onClick={onClose} style={{ padding: "2px 8px", fontSize: 13 }}>×</button>
          </div>

          {!info && !error && (
            <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>Laden…</p>
          )}

          {error && (
            <p style={{ color: "var(--red)", fontSize: 12, margin: 0 }}>{error}</p>
          )}

          {info && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <Row label="Projekt" value={info.name} />
              <Row
                label="Externe URL"
                value={info.externalUrl || <span style={{ color: "var(--muted)", fontStyle: "italic" }}>nicht konfiguriert</span>}
              />
              <Row
                label="Token"
                value={info.tokenHash
                  ? <span style={{ fontFamily: "monospace" }}>{info.tokenHash}…</span>
                  : <span style={{ color: "var(--muted)", fontStyle: "italic" }}>kein Token</span>
                }
              />
            </div>
          )}

          <button
            onClick={handleShowQr}
            disabled={loadingQr || !info?.externalUrl || !info?.tokenHash}
            className="primary"
            style={{ width: "100%" }}
            title={!info?.externalUrl ? "Starte den Server mit --external-url" : undefined}
          >
            {loadingQr ? "Generiere…" : "QR-Code anzeigen"}
          </button>

          <p style={{ color: "var(--muted)", fontSize: 11, margin: 0, lineHeight: 1.4 }}>
            Der Token im QR-Code wird nach dem Scan durch die PWA sofort rotiert.
          </p>
        </div>
      </div>

      {qrPayload && (
        <QrCodeOverlay
          payload={qrPayload}
          onClose={() => setQrPayload(null)}
        />
      )}
    </>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <span style={{ fontSize: 10, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.5 }}>
        {label}
      </span>
      <span style={{ fontSize: 13, color: "var(--text)", wordBreak: "break-all" }}>{value}</span>
    </div>
  );
}
