import { useEffect, useRef } from "react";
import QRCode from "qrcode";
import { QrPayload } from "../api";

interface Props {
  payload: QrPayload;
  onClose: () => void;
}

export default function QrCodeOverlay({ payload, onClose }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    const json = JSON.stringify({ sdd: payload.sdd, name: payload.name, url: payload.url, token: payload.token });
    QRCode.toCanvas(canvasRef.current, json, {
      width: 280,
      margin: 2,
      color: { dark: "#000000", light: "#ffffff" },
    }).catch(console.error);
  }, [payload]);

  function handleBackdrop(e: React.MouseEvent) {
    if (e.target === e.currentTarget) onClose();
  }

  return (
    <div
      onClick={handleBackdrop}
      style={{
        position: "fixed", inset: 0,
        background: "rgba(0,0,0,0.7)",
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: 12,
        padding: 24,
        display: "flex", flexDirection: "column", alignItems: "center", gap: 16,
        maxWidth: 340,
      }}>
        <h3 style={{ margin: 0, color: "var(--accent)", fontSize: 15 }}>
          Mit PWA verbinden
        </h3>

        <div style={{
          background: "#fff",
          padding: 12,
          borderRadius: 8,
          display: "inline-block",
          lineHeight: 0,
        }}>
          <canvas ref={canvasRef} />
        </div>

        <div style={{ textAlign: "center", fontSize: 12, color: "var(--muted)", lineHeight: 1.5 }}>
          <div style={{ fontWeight: 600, color: "var(--text)", marginBottom: 4 }}>{payload.name}</div>
          <div style={{ fontFamily: "monospace", wordBreak: "break-all" }}>{payload.url}</div>
          <div style={{ marginTop: 6, color: "var(--yellow)" }}>
            Token wird nach dem Scan sofort rotiert.
          </div>
        </div>

        <button onClick={onClose} style={{ width: "100%" }}>Schliessen</button>
      </div>
    </div>
  );
}
