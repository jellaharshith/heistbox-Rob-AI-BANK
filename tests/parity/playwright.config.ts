import { defineConfig } from "@playwright/test";

/**
 * HeistBox parity suite. The SAME specs run unmodified against:
 *   - the baseline Next.js app:  PARITY_BASE_URL=http://localhost:3000 (default)
 *   - the new Vite 3D app:       PARITY_BASE_URL=http://localhost:5173
 * PARITY_API_URL is the FastAPI backend the app under test talks to; it is only used as a
 * read-only oracle (e.g. "are any sponsor keys missing?"), never to stub the UI.
 * PARITY_LABEL picks the screenshot folder: tests/screens/<label>/ (default "baseline").
 */
const baseURL = process.env.PARITY_BASE_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir: "./specs",
  timeout: 120_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  // The backend vault is global state (counters, settlements), so specs run one at a time.
  workers: Number(process.env.PARITY_WORKERS ?? 1),
  retries: Number(process.env.PARITY_RETRIES ?? 0),
  reporter: [["list"], ["json", { outputFile: "results/results.json" }], ["html", { open: "never", outputFolder: "results/html" }]],
  outputDir: "results/artifacts",
  use: {
    baseURL,
    viewport: { width: 1440, height: 900 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    // A fake webcam so the mugshot cam goes live and the poster gets a real frame.
    permissions: ["camera", "microphone"],
    launchOptions: { args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"] },
  },
  projects: [
    { name: "parity", testIgnore: /screens\.spec\.ts/ },
    { name: "screens", testMatch: /screens\.spec\.ts/ },
  ],
});
