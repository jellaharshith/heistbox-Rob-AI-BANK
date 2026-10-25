import { test, expect } from '@playwright/test';
test('six immutable models render, named camera and distance LODs hold', async ({ page }) => {
  const errors:string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if(m.type() === 'error') errors.push(m.text()); });
  await page.goto('/');
  await page.waitForFunction(() => (window as any).__heist?.store.getState().ready);
  await expect(page.locator('.loading')).toHaveCount(0);
  await page.waitForTimeout(1200);
  const initial = await page.evaluate(() => {
    const h=(window as any).__heist;
    return { calls:h.renderer.info.render.calls, triangles:h.renderer.info.render.triangles, camera:h.camera.position.toArray() };
  });
  expect(initial.calls).toBeLessThanOrEqual(60);
  expect(initial.triangles).toBeLessThan(150000);
  expect(initial.camera[2]).toBeCloseTo(5.6,1);
  // Exercise actual frame updates at three distances, including split-material Tina meshes.
  for (const [z,level] of [[-1,0],[8,1],[20,2]]) {
    const visible = await page.evaluate(async ({z}) => {
      const h=(window as any).__heist;
      const tina=h.scene.getObjectByName('CHAR_Tina');
      const root=tina.parent;
      root.position.z=z;
      await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      const nodes:any[]=[];
      tina.traverse((n:any) => { if(/_LOD[012](?:_|$)/.test(n.name)) nodes.push({name:n.name,visible:n.visible}); });
      return nodes;
    }, {z:5.6-z});
    expect(visible.length).toBeGreaterThan(2);
    for(const n of visible) expect(n.visible, JSON.stringify({z,level,n})).toBe(Number(n.name.match(/_LOD([012])/)[1])===level);
  }
  expect(errors).toEqual([]);
  await page.screenshot({path:'test-results/step1-verified.png'});
});





