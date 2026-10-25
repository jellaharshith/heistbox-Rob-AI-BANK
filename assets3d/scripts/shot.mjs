// Headless screenshot of the viewer through Chrome.
//   node scripts/shot.mjs --src export/CHAR_Tina.glb|/CHAR_Tina.glb --out shots/x.png [--clip Name --t 0.5] [--view front] [--morph viseme_PP:1,jawOpen:.3]
//        [--pose rest] [--size 640x800] [--hide nodeA,nodeB] [--lod 0]
// Starts its own vite server on a free-ish port unless VIEWER_URL is set. Pass several shots with --batch shots.json ([{...}]).
import { chromium } from 'playwright';
import { createServer } from 'vite';
import path from 'path';
import fs from 'fs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, all) => (v.startsWith('--') ? [...a, [v.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : true]] : a), []));
const jobs = args.batch ? JSON.parse(fs.readFileSync(args.batch, 'utf8').replace(/^\uFEFF/, '')) : [args];
const port = 5200 + Math.floor(Math.random() * 700);
const server = await createServer({ configFile: path.resolve(import.meta.dirname, '../viewer/vite.config.js'), server: { port, strictPort: false }, logLevel: 'silent' });
await server.listen();
const base = `http://localhost:${server.config.server.port}`;
const browser = await chromium.launch({ channel: 'chrome', args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
let failed = 0;
for (const j of jobs) {
  let src = String(j.src);
  if (!src.startsWith('/')) src = '/@fs/' + path.resolve(src).replace(/\\/g, '/');
  else if (/^[A-Za-z]:/.test(src)) src = '/@fs/' + src.replace(/\\/g, '/');
  const [w, h] = (j.size || '640x800').split('x').map(Number);
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  const errs = []; page.on('pageerror', e => errs.push(e.message)); page.on('console', m => m.type() === 'error' && !/favicon|404/.test(m.text() + (m.location().url||'')) && errs.push(m.text()));
  const qs = new URLSearchParams({ src }); for (const k of ['clip', 't', 'view', 'morph', 'pose', 'hide']) if (j[k] !== undefined && j[k] !== true) qs.set(k, j[k]);
  await page.goto(`${base}/?${qs}`);
  try { await page.waitForFunction(() => window.__viewer && (window.__viewer.ready || window.__viewer.error), null, { timeout: 60000 }); } catch { errs.push('timeout waiting for viewer'); }
  if (j.lod !== undefined) await page.evaluate(l => window.__viewer.showLOD(l), j.lod);
  if (j.hideui !== 'false') await page.evaluate(() => (document.getElementById('ui').style.display = 'none'));
  await page.waitForTimeout(400);
  const out = path.resolve(j.out); fs.mkdirSync(path.dirname(out), { recursive: true });
  await page.screenshot({ path: out });
  const err = await page.evaluate(() => window.__viewer && window.__viewer.error);
  if (err || errs.length) { failed++; console.log('FAIL', out, err || '', errs.slice(0, 3).join(' | ')); } else console.log('shot', out);
  await page.close();
}
await browser.close(); await server.close();
process.exit(failed ? 1 : 0);


