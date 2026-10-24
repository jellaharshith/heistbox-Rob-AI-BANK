import { test, expect } from "@playwright/test";

test.use({ launchOptions: { args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"] } });

test.describe("opt-in mugshot flow", () => {
  test("capture, retake, and skip are available", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("button", { name: "TAKE MUGSHOT" })).toBeVisible();
    await expect(page.getByRole("button", { name: "SKIP" })).toBeVisible();
    await page.getByRole("button", { name: "TAKE MUGSHOT" }).click();
    await expect(page.getByText("Your photo stays in your browser.")).toBeVisible();
    await page.getByRole("button", { name: "TAKE PHOTO" }).click();
    await expect(page.getByText("Review your mugshot")).toBeVisible({ timeout: 5000 });
    await page.getByRole("button", { name: "RETAKE" }).click();
    await expect(page.getByRole("button", { name: "TAKE PHOTO" })).toBeVisible();
    await page.getByRole("button", { name: "CANCEL" }).click();
    await page.getByRole("button", { name: "SKIP" }).click();
    await expect(page.getByText("Break the vault.")).toBeVisible();
  });

  test("permission denial falls back to avatar without an error dialog", async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, "mediaDevices", { value: { getUserMedia: () => Promise.reject(new DOMException("denied", "NotAllowedError")) } });
    });
    await page.goto("/");
    await page.getByRole("button", { name: "TAKE MUGSHOT" }).click();
    await expect(page.getByText(/Camera unavailable/)).toBeVisible();
    await expect(page.locator("[role=dialog]")).toHaveCount(0);
  });

  test("AI is opt-in and off means no Gemini request receives an image", async ({ page }) => {
    const requests: string[] = [];
    page.on("request", (request) => requests.push(`${request.method()} ${request.url()} ${request.postData() ?? ""}`));
    await page.goto("/");
    await page.getByRole("button", { name: "TAKE MUGSHOT" }).click();
    await expect(page.getByRole("checkbox", { name: /Let AI describe/ })).not.toBeChecked();
    await page.getByRole("button", { name: "SKIP" }).click();
    expect(requests.filter((request) => request.includes("generativelanguage.googleapis.com"))).toHaveLength(0);
    expect(requests.join("\n")).not.toContain("inline_data");
  });

  test("wanted poster downloads as a browser-generated PNG", async ({ page }) => {
    await page.clock.install();
    await page.goto("/");
    await page.getByRole("button", { name: "SKIP" }).click();
    await page.clock.fastForward(91_000);
    await expect(page.getByRole("heading", { name: "Wanted Poster" })).toBeVisible();
    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "DOWNLOAD PNG" }).click();
    await expect((await download).suggestedFilename()).toBe("heistbox-wanted-poster.png");
  });
});
