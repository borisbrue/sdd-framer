import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

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
  },
});
