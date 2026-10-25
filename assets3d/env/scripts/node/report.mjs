// Pack report generator: node report.mjs  -> assets3d/PACK_REPORT.md
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { imageSize } from 'image-size';
import fs from 'fs';
const A = 'C:/Users/Shaik/Downloads/heistbox/assets3d';
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);

const PACK = [
  { name: 'CHAR_Tina', dir: 'tina', texMax: 2048, glbMB: 4 },
  { name: 'CHAR_Heister', dir: 'heister', texMax: 1024, glbMB: 4 },
  { name: 'CHAR_Customer', dir: 'customer', texMax: 1024, glbMB: 4 },
  { name: 'CHAR_Sentinel', dir: 'mech', texMax: 1024, glbMB: 4 },
  { name: 'ENV_Bank', dir: 'env', texMax: 1024, glbMB: 99 },
  { name: 'PROPS', dir: 'env', texMax: 1024, glbMB: 99 },
];
const pick = (dir, name) => {
  // raw (uncompressed) and optimized candidates in <dir>/export
  const raw = `${A}/${dir}/export/${name}.glb`, opt = `${A}/${dir}/export/${name}.opt.glb`;
  return { raw: fs.existsSync(raw) ? raw : null, opt: fs.existsSync(opt) ? opt : null };
};
const fmt = (n) => n.toLocaleString('en-US');
const mb = (b) => (b / 1048576).toFixed(2) + ' MB';
const lodOf = (n) => { const m = /LOD(\d)/i.exec(n); return m ? +m[1] : 0; };

const flags = [];
const sections = [];
let totTris = 0, totDraws = 0, totBytes = 0; const allMats = new Set();
const summary = [];

for (const p of PACK) {
  const { raw, opt } = pick(p.dir, p.name);
  if (!raw && !opt) { sections.push(`## ${p.name}\n\nMISSING (no GLB in ${p.dir}/export)\n`); flags.push(`${p.name}: file missing`); continue; }
  const doc = await io.read(raw || opt);
  const root = doc.getRoot();
  const rows = []; let tris = 0, draws = 0, trisAll = 0;
  for (const node of root.listNodes()) {
    const mesh = node.getMesh(); if (!mesh) continue;
    let t = 0, pr = 0;
    for (const prim of mesh.listPrimitives()) {
      const idx = prim.getIndices(); const pos = prim.getAttribute('POSITION');
      t += Math.floor((idx ? idx.getCount() : pos.getCount()) / 3); pr++;
    }
    const lod = lodOf(node.getName());
    const targets = mesh.listPrimitives()[0]?.listTargets().length || 0;
    rows.push({ name: node.getName(), tris: t, prims: pr, lod, morph: targets, skinned: !!node.getSkin(), mats: [...new Set(mesh.listPrimitives().map(x => x.getMaterial()?.getName() || '(none)'))] });
    trisAll += t;
    if (lod === 0) { tris += t; draws += pr; }
  }
  const joints = root.listSkins().reduce((a, s) => Math.max(a, s.listJoints().length), 0);
  const mats = root.listMaterials().map(m => m.getName());
  mats.forEach(m => allMats.add(m));
  const tex = root.listTextures().map(t => {
    let dims = '?'; try { const d = imageSize(t.getImage()); dims = `${d.width}x${d.height}`; } catch (e) {}
    return { name: t.getName() || t.getURI() || '(tex)', dims, mime: t.getMimeType() };
  });
  // use optimized file for texture dims/size if available
  let optTex = tex, optSize = raw ? fs.statSync(raw).size : 0;
  if (opt) { optSize = fs.statSync(opt).size;
    const d2 = await io.read(opt).catch(() => null);
    if (d2) optTex = d2.getRoot().listTextures().map(t => { let dims = '?'; try { const d = imageSize(t.getImage()); dims = `${d.width}x${d.height}`; } catch (e) {} return { name: t.getName() || '(tex)', dims, mime: t.getMimeType() }; });
  }
  totBytes += optSize; totTris += tris; totDraws += draws;
  const anims = root.listAnimations().map(a => a.getName());
  // budget checks
  for (const r of rows) {
    let lim = 3000;
    if (/^CHAR_/.test(p.name)) lim = p.name === 'CHAR_Sentinel' ? 2500 : [15000, 7000, 3000][r.lod] ?? 15000;
    if (/^VAULT_.*_Door/.test(r.name)) lim = 6000;
    if (/^ENV_/.test(r.name) || p.name === 'ENV_Bank') lim = 60000;
    if (r.tris > lim && !(p.name === 'ENV_Bank')) flags.push(`${p.name}/${r.name}: ${fmt(r.tris)} tris > ${fmt(lim)}`);
  }
  if (p.name === 'ENV_Bank' && trisAll > 60000) flags.push(`ENV_Bank hall ${fmt(trisAll)} tris > 60k`);
  if (joints > 65) flags.push(`${p.name}: ${joints} bones > 65`);
  if (optSize > p.glbMB * 1048576) flags.push(`${p.name}: optimized ${mb(optSize)} > ${p.glbMB} MB`);
  for (const t of optTex) { const w = parseInt(t.dims); if (w > p.texMax) flags.push(`${p.name}: texture ${t.name} ${t.dims} > ${p.texMax}`); }
  const md = [];
  md.push(`## ${p.name}`, '');
  md.push(`- Source: \`${(raw || opt).replace(A + '/', '')}\` (tris counted from uncompressed GLB); optimized: ${opt ? '`' + opt.replace(A + '/', '') + '`' : 'NONE'}`);
  md.push(`- File size: raw ${raw ? mb(fs.statSync(raw).size) : 'n/a'}, optimized ${opt ? mb(optSize) : 'n/a'}`);
  md.push(`- Scene tris (LOD0 only): **${fmt(tris)}**; all LODs: ${fmt(trisAll)}; draw calls (primitives, LOD0): **${draws}**`);
  md.push(`- Materials (${mats.length}): ${mats.join(', ')}`);
  md.push(`- Bones: ${joints}; morph-target meshes: ${rows.filter(r => r.morph).map(r => `${r.name}(${r.morph})`).join(', ') || 'none'}`);
  md.push(`- Animations (${anims.length}): ${anims.join(', ') || 'none'}`);
  md.push(`- Textures (${optTex.length}): ${optTex.map(t => `${t.name} ${t.dims}`).join('; ') || 'none'}`, '');
  md.push('| Object | Tris | Prims | LOD | Skinned | Materials |', '|---|---:|---:|---:|---|---|');
  for (const r of rows) md.push(`| ${r.name} | ${fmt(r.tris)} | ${r.prims} | ${r.lod} | ${r.skinned ? 'yes' : ''} | ${r.mats.join(', ')} |`);
  md.push('');
  sections.push(md.join('\n'));
  summary.push(`| ${p.name} | ${fmt(tris)} | ${draws} | ${mats.length} | ${joints} | ${optTex.length} | ${opt ? mb(optSize) : 'n/a (raw ' + mb(optSize) + ')'} |`);
}

const out = [];
out.push('# HeistBox x PAIR asset pack - PACK_REPORT', '', `Generated ${new Date().toISOString()}`, '');
out.push('## Scene-wide totals', '');
out.push('| File | Scene tris (LOD0) | Draw calls | Materials | Bones | Textures | Optimized size |', '|---|---:|---:|---:|---:|---:|---:|', ...summary);
out.push('', `- **Total scene tris: ${fmt(totTris)}** (budget 150,000) ${totTris <= 150000 ? 'OK' : 'OVER'}`);
out.push(`- **Total draw calls (primitives, LOD0, all files loaded at once): ${totDraws}** (budget 40) ${totDraws <= 40 ? 'OK' : 'OVER'}`);
out.push(`- **Total unique materials: ${allMats.size}**`);
out.push(`- **Pack size (optimized GLBs): ${mb(totBytes)}** (budget 25 MB) ${totBytes <= 25 * 1048576 ? 'OK' : 'OVER'}`, '');
if (totTris > 150000) flags.push(`Scene tris ${fmt(totTris)} > 150k`);
if (totDraws > 40) flags.push(`Draw calls ${totDraws} > 40`);
if (totBytes > 25 * 1048576) flags.push(`Pack size ${mb(totBytes)} > 25 MB`);
out.push('## Flags (over-budget / issues)', '', flags.length ? flags.map(f => '- ' + f).join('\n') : '- none', '');
out.push(...sections);
fs.writeFileSync(A + '/PACK_REPORT.md', out.join('\n'));
console.log(out.slice(0, 22).join('\n'));
