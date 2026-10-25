import { test, expect } from "@playwright/test";
test("mock sequence completes, reset reuses assets, skip cancels pending work", async ({
  page,
}) => {
  test.setTimeout(120000);
  const errors: string[] = [];
  const loadedModels: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  page.on("request", (r) => {
    if (r.url().endsWith(".glb")) loadedModels.push(r.url());
  });
  await page.goto("/");
  await page.waitForFunction(
    () => (window as any).__heist?.store.getState().ready,
  );
  await page.evaluate(() => {
    const h = (window as any).__heist;
    h.history = [];
    h.store.subscribe((s: any, p: any) => {
      if (s.stage !== p.stage) h.history.push(s.stage);
    });
  });
  await page.getByRole("button", { name: "Try the $5,000 favor" }).click();
  await page.getByRole("button", { name: "Attempt heist" }).click();
  await expect(page.getByRole("region", { name: "Heist results" })).toBeVisible(
    { timeout: 45000 },
  );
  await expect(page.getByTestId("vault-L")).toContainText("$5,000");
  await expect(page.getByTestId("vault-M")).toContainText("FROZEN");
  await expect(page.getByTestId("vault-R")).toContainText("APPROVED");
  await expect(page.locator(".timings")).toContainText("0.42");
  await expect(page.locator(".timings")).toContainText("0.81");
  expect(await page.evaluate(() => (window as any).__heist.history)).toEqual([
    "proposal",
    "llm",
    "firewall",
    "slam",
    "scan",
    "fire",
    "roast",
    "poster",
    "refund",
    "faceid",
    "settlement",
    "complete",
  ]);
  await page.screenshot({
    path: "test-results/step2-results.png",
    fullPage: true,
  });
  const before = await page.evaluate(() => {
    const h = (window as any).__heist;
    return {
      textures: h.renderer.info.memory.textures,
      geometries: h.renderer.info.memory.geometries,
    };
  });
  for (let i = 0; i < 20; i++) {
    await page.getByRole("button", { name: "Try another heist" }).click();
    await expect(page.getByTestId("vault-L")).toContainText("$0");
    await page.getByRole("button", { name: "Attempt heist" }).click();
    await page.getByRole("button", { name: "Skip sequence" }).click();
    await expect(
      page.getByRole("region", { name: "Heist results" }),
    ).toBeVisible();
  }
  await page.getByRole("button", { name: "Try another heist" }).click();
  await page.waitForTimeout(1600);
  expect(
    await page.evaluate(() => (window as any).__heist.store.getState().phase),
  ).toBe("LOBBY");
  const after = await page.evaluate(() => {
    const h = (window as any).__heist;
    return {
      textures: h.renderer.info.memory.textures,
      geometries: h.renderer.info.memory.geometries,
    };
  });
  expect(after.textures).toBeLessThanOrEqual(before.textures);
  expect(after.geometries).toBeLessThanOrEqual(before.geometries);
  expect(loadedModels).toHaveLength(6);
  expect(errors).toEqual([]);
});
test("mobile layout and camera-off flow never request media; M ignores typing", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => {
    (window as any).mediaRequests = 0;
    navigator.mediaDevices.getUserMedia = async () => {
      (window as any).mediaRequests++;
      throw Error("Unexpected capture");
    };
  });
  await page.goto("/");
  await page.waitForFunction(
    () => (window as any).__heist?.store.getState().ready,
  );
  await page.getByRole("button", { name: "Camera off" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Continue without camera" }).click();
  expect(await page.evaluate(() => (window as any).mediaRequests)).toBe(0);
  await page.getByRole("textbox").fill("money");
  expect(
    await page.evaluate(() => (window as any).__heist.store.getState().mock),
  ).toBe(true);
  await page.getByRole("textbox").blur();
  await page.keyboard.press("m");
  await expect(page.locator(".status")).toContainText("LIVE");
  await page.getByRole("button", { name: "Attempt heist" }).click();
  await expect(page.getByRole("alert")).toContainText("step 5");
  await page.keyboard.press("m");
  await expect(page.locator(".status")).toContainText("MOCK");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/step2-mobile.png",
    fullPage: true,
  });
});
