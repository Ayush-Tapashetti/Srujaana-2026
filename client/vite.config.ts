import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The browser always calls relative /api paths and Vite forwards them.
// No CORS to configure, and the same build works in Docker and locally.
// In Docker the server is reachable as http://server:8000.
const target = process.env.VITE_API_PROXY ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target, changeOrigin: true } },
    // Docker on Windows often doesn't pass file-change events into the
    // container, so live reload stops. Polling fixes it at a small CPU cost.
    watch: { usePolling: process.env.VITE_USE_POLLING === "true" },
  },
  preview: {
    port: 5173,
    proxy: { "/api": { target, changeOrigin: true } },
  },
});
