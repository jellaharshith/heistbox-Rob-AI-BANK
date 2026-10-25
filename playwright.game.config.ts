import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";
import path from "node:path";
const localBrowser = path.join(
  process.env.LOCALAPPDATA || "",
  "ms-playwright/chromium-1194/chrome-win/chrome.exe",
);
export default defineConfig({
  testDir: "tests/game",
  workers: 1,
  timeout: 60000,
  use: {
    baseURL: "http://127.0.0.1:5173",
    viewport: { width: 1440, height: 1000 },
    launchOptions: {
      executablePath:
        process.env.PLAYWRIGHT_EXECUTABLE_PATH ||
        (existsSync(localBrowser) ? localBrowser : undefined),
      args: process.platform === "win32" ? ["--use-angle=d3d11"] : [],
    },
  },
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: true,
    timeout: 60000,
  },
});
