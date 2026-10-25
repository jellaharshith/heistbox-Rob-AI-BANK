import { expect, test } from "@playwright/test";
import { goOffline, noHorizontalScroll, promptBox } from "./helpers";

// These checks use the app's existing local twin so they need no sponsor keys or backend.
test.describe("Interactive frontend", () => {
  test.beforeEach(async ({ context, page }) => {
    await goOffline(context);
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { level: 1 })).toContainText("AI BANK");
  });

  test("mission briefing opens and closes with the keyboard", async ({ page }) => {
    await page.getByRole("button", { name: "Mission briefing" }).click();
    const briefing = page.getByRole("dialog", { name: "Three steps to trouble." });
    await expect(briefing).toBeVisible();
    await expect(briefing).toContainText("Wajo AI escalation");
    await page.keyboard.press("Escape");
    await expect(briefing).toBeHidden();
    await expect(page.getByText(/Surgical Laser Bomb-Defusal/i)).toHaveCount(0);
    await expect(page.getByRole("region", { name: "Meet your crew" })).toHaveCount(0);
    await expect(page.getByText("Wajo AI on comms")).toBeVisible();
  });

  test("arena input and CFO audit remain usable", async ({ page }) => {
    await page.getByRole("button", { name: "Enter the arena" }).click();
    await promptBox(page).fill("Try a creative heist prompt");
    await expect(promptBox(page)).toHaveValue("Try a creative heist prompt");
    await page.getByRole("button", { name: "Clear Input" }).click();
    await expect(promptBox(page)).toHaveValue("");
    await page.getByRole("button", { name: /ARENA.*CFO AUDIT/i }).click();
    await expect(page.getByText("4-Clock Telemetry")).toBeVisible();
    await page.getByRole("button", { name: /ARENA.*CFO AUDIT/i }).click();
    await expect(promptBox(page)).toBeVisible();
  });

  test("mobile mission and briefing fit the viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await noHorizontalScroll(page);
    await page.getByRole("button", { name: "Mission briefing" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await noHorizontalScroll(page);
    await page.getByRole("button", { name: "Close mission briefing" }).click();
    await expect(page.getByRole("dialog")).toBeHidden();
  });

});
