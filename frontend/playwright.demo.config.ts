// Runs the same E2E scenarios against the static demo build (no backend running).
import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: "http://localhost:4173" },
  webServer: { command: "npx vite preview --port 4173", url: "http://localhost:4173", reuseExistingServer: true },
});
