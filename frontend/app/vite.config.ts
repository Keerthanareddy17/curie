/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  // strictPort: without it, Vite silently falls back to 5174+ when 5173 is
  // taken, and the backend's CORS allowlist (curie/backend/api/app.py) only
  // trusts 5173 — a silent fallback here means every browser request fails
  // as an opaque CORS error instead of the dev server refusing to start.
  server: { port: 5173, strictPort: true },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
});
