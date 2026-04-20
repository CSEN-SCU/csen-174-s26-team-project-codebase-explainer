import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const apiProxy = {
  "/api": {
    target: "http://127.0.0.1:8001",
    changeOrigin: true,
  },
};

export default defineConfig({
  // Load .env from this folder even if the shell cwd differs.
  envDir: __dirname,
  plugins: [react()],
  server: {
    port: 5173,
    proxy: apiProxy,
  },
  // Same proxy for `npm run preview` so /api/* reaches the backend (avoids opaque "404" errors).
  preview: {
    port: 4173,
    proxy: apiProxy,
  },
});
