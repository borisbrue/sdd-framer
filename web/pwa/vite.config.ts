import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "fs";
import path from "path";

const CERT_DIR = path.resolve(__dirname, "../../.certs");
const certExists = fs.existsSync(path.join(CERT_DIR, "cert.pem"));

// SPEC-0025 FR-09: base: '/' — deploybar auf beliebigem Static-File-Server
export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: "dist",
    sourcemap: true,
  },
  server: {
    port: 5174,
    host: true,
    https: certExists
      ? {
          cert: fs.readFileSync(path.join(CERT_DIR, "cert.pem")),
          key: fs.readFileSync(path.join(CERT_DIR, "key.pem")),
        }
      : undefined,
  },
});
