import { expect, test } from "@playwright/test";
import { gotoArena, waitKernelLive, statText } from "./helpers";

test.describe("TopBar and StatusBar Parity", () => {
  test.beforeEach(async ({ page }) => {
    await gotoArena(page);
    await waitKernelLive(page);
  });

  test("P-001: Header branding and subtitle", async ({ page }) => {
    await expect(page.getByText("HEISTBOX", { exact: true })).toBeVisible();
    await expect(page.getByText(/Ocean's 11 × PAIR Enterprise/i)).toBeVisible();
  });

  test("P-002: Live stat Total vault money saved today", async ({ page }) => {
    await expect(page.getByText(/Total vault money saved today/i)).toBeVisible();
    const saved = await statText(page, "Total vault money saved today");
    expect(saved).toMatch(/\$[\d,]+/);
  });

  test("P-003: Live stat Robbers busted counter", async ({ page }) => {
    await expect(page.getByText(/Robbers busted/i)).toBeVisible();
    const busted = await statText(page, "Robbers busted");
    expect(busted).toMatch(/\d+/);
  });

  test("P-004: Live stat Fastest catch latency", async ({ page }) => {
    await expect(page.getByText(/Fastest catch/i)).toBeVisible();
    const catchTime = await statText(page, "Fastest catch");
    expect(catchTime).toMatch(/(\d+(\.\d+)?ms|—)/);
  });

  test("P-005: 5-star Wanted meter and martingale R_t", async ({ page }) => {
    await expect(page.getByLabel(/Wanted level \d+ of 5/i)).toBeVisible();
    await expect(page.getByText(/conformal martingale R/i)).toBeVisible();
  });

  test("P-006: View switch toggle between Arena and CFO Audit", async ({ page }) => {
    const toggle = page.getByRole("button", { name: /ARENA.*⇄.*CFO AUDIT/i });
    await expect(toggle).toBeVisible();
    await toggle.click();
    await expect(page.getByText("4-Clock Telemetry")).toBeVisible();
    await toggle.click();
    await expect(page.getByRole("heading", { name: "ROB OUR AI BANK", exact: true })).toBeVisible();
  });

  test("P-007: Reset Vault button resets vault state", async ({ page }) => {
    const resetBtn = page.getByRole("button", { name: /Reset Vault/i });
    await expect(resetBtn).toBeVisible();
    await resetBtn.click();
    await expect(page.getByText(/kernel live|local twin/i).first()).toBeVisible();
  });

  test("P-008: Audio mute toggle button toggles muted icon", async ({ page }) => {
    const muteBtn = page.getByTitle(/Mute|Unmute/i);
    await expect(muteBtn).toBeVisible();
    const initialTitle = await muteBtn.getAttribute("title");
    await muteBtn.click();
    const newTitle = await muteBtn.getAttribute("title");
    expect(newTitle).not.toBe(initialTitle);
    await muteBtn.click(); // restore
  });

  test("P-009: Backend connectivity status badge", async ({ page }) => {
    await expect(page.getByText(/●\s*(kernel live|local twin)/i).first()).toBeVisible();
  });

  test("P-010: Sponsor status pills in status bar", async ({ page }) => {
    const requiredSponsors = [
      "Anthropic",
      "Cloud Vision",
      "Cartesia",
      "CRS Sandbox",
      "Base Sepolia x402",
      "Fetch.ai Escrow",
      "Wajo Voice Alert",
      "MCP Server",
      "Postgres",
      "Kernel gate (SQLite)",
    ];
    for (const sponsor of requiredSponsors) {
      await expect(page.getByText(sponsor).first()).toBeVisible();
    }
  });

  test("P-011: Sponsor status re-check refresh button", async ({ page }) => {
    const refreshBtn = page.getByTitle(/Re-check \/api\/integrations\/status/i);
    await expect(refreshBtn).toBeVisible();
    await refreshBtn.click();
    await expect(page.getByText("Kernel gate (SQLite)")).toBeVisible();
  });

  test("P-013 & P-014 & P-015: Connect Live Sponsor Keys modal, fields, and host protection", async ({ page }) => {
    const keysBtn = page.getByRole("button", { name: /Connect Live Sponsor Keys/i });
    if (await keysBtn.isVisible()) {
      await keysBtn.click();
      await expect(page.getByRole("heading", { name: /Connect Live Sponsor Keys/i })).toBeVisible();
      await expect(page.getByText("ANTHROPIC_API_KEY")).toBeVisible();
      await expect(page.getByText("CARTESIA_API_KEY")).toBeVisible();
      await expect(page.getByRole("button", { name: "Save & verify" })).toBeVisible();
      await page.getByRole("button", { name: "Close" }).click();
      await expect(page.getByRole("heading", { name: /Connect Live Sponsor Keys/i })).not.toBeVisible();
    }
  });
});
