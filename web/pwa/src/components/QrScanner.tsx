import { useEffect, useRef } from "react";
import jsQR from "jsqr";

interface Props {
  onDetected: (data: string) => void;
  onError: (msg: string) => void;
}

/**
 * QrScanner — jsQR-basierter Kamera-Stream-Scanner.
 *
 * Nutzt getUserMedia (environment-facing camera) und fragt jeden Animation-Frame
 * mit jsQR ab. Ruft onDetected beim ersten Fund auf und stoppt danach automatisch.
 * Funktioniert auf iOS Safari + Android Chrome ohne native Barcode-API.
 */
export default function QrScanner({ onDetected, onError }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);
  const detectedRef = useRef(false);

  useEffect(() => {
    let stream: MediaStream | null = null;

    async function startCamera() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
        });
      } catch {
        onError("Kamera-Zugriff verweigert. Bitte Berechtigung erteilen.");
        return;
      }

      const video = videoRef.current;
      if (!video) return;
      video.srcObject = stream;
      video.setAttribute("playsinline", "true"); // wichtig für iOS
      await video.play().catch(() => undefined);
      rafRef.current = requestAnimationFrame(tick);
    }

    function tick() {
      if (detectedRef.current) return;
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas) return;

      if (video.readyState < video.HAVE_ENOUGH_DATA) {
        rafRef.current = requestAnimationFrame(tick);
        return;
      }

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      ctx.drawImage(video, 0, 0);
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const code = jsQR(imageData.data, canvas.width, canvas.height, {
        inversionAttempts: "dontInvert",
      });

      if (code) {
        detectedRef.current = true;
        onDetected(code.data);
        return; // kein weiterer Frame nach Fund
      }

      rafRef.current = requestAnimationFrame(tick);
    }

    startCamera();

    return () => {
      cancelAnimationFrame(rafRef.current);
      stream?.getTracks().forEach(t => t.stop());
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={styles.wrapper}>
      <video
        ref={videoRef}
        muted
        playsInline
        style={styles.video}
      />
      {/* Unsichtbares Canvas für jsQR-Pixel-Analyse */}
      <canvas ref={canvasRef} style={{ display: "none" }} />

      {/* Zielrahmen-Overlay */}
      <div style={styles.overlay}>
        <div style={styles.corner("topLeft")} />
        <div style={styles.corner("topRight")} />
        <div style={styles.corner("bottomLeft")} />
        <div style={styles.corner("bottomRight")} />
      </div>
    </div>
  );
}

type Corner = "topLeft" | "topRight" | "bottomLeft" | "bottomRight";

const CORNER_SIZE = 24;
const CORNER_WIDTH = 3;

const styles = {
  wrapper: {
    position: "relative" as const,
    width: "100%",
    aspectRatio: "1",
    maxWidth: 320,
    margin: "0 auto",
    background: "#000",
    borderRadius: 12,
    overflow: "hidden",
  },
  video: {
    width: "100%",
    height: "100%",
    objectFit: "cover" as const,
    display: "block",
  },
  overlay: {
    position: "absolute" as const,
    inset: 0,
  },
  corner: (which: Corner): React.CSSProperties => {
    const isTop = which.startsWith("top");
    const isLeft = which.endsWith("Left");
    return {
      position: "absolute",
      width: CORNER_SIZE,
      height: CORNER_SIZE,
      [isTop ? "top" : "bottom"]: 20,
      [isLeft ? "left" : "right"]: 20,
      borderTop: isTop ? `${CORNER_WIDTH}px solid var(--accent)` : "none",
      borderBottom: !isTop ? `${CORNER_WIDTH}px solid var(--accent)` : "none",
      borderLeft: isLeft ? `${CORNER_WIDTH}px solid var(--accent)` : "none",
      borderRight: !isLeft ? `${CORNER_WIDTH}px solid var(--accent)` : "none",
    };
  },
};
