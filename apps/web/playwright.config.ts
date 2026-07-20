import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://localhost:3100",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "go run ./cmd/server",
      cwd: "../../services/api",
      url: "http://localhost:8180/api/v1/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npm run dev",
      url: "http://localhost:3100",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
