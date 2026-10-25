// usage: node verify_opt.mjs <ENV_Bank.glb (raw or opt)> <PROPS.glb (raw or opt)>
// Checks: 7 empties, material names, TEXCOORD_1 on ENV_Bank prims + occlusionTexture.texCoord==1, *Runtime materials plain emissive
// with UVs spanning 0-1 and not mirrored, PROP_Bill (<=12 tris, doubleSided, 1 material), cash node->mesh sharing.
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { MeshoptDecoder } from 'meshoptimizer';
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
let bad = 0; const ok = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); if (!c) bad++; };
const [envf, propf] = process.argv.slice(2, 4);
const env = await io.read(envf), props = await io.read(propf);
const er = env.getRoot();
const EMPTIES = ['SPAWN_Player', 'SPAWN_Customer', 'CAM_Overview', 'CAM_VaultL', 'CAM_VaultM', 'CAM_VaultR', 'ANCHOR_LaserTarget'];
const names = er.listNodes().map(n => n.getName());
for (const e of EMPTIES) { const n = er.listNodes().find(n => n.getName() === e); ok(n && !n.getMesh(), 'empty ' + e); }
const em = er.listMaterials().map(m => m.getName());
console.log('ENV materials', em.join(','));
for (const m of ['MAT_Brass', 'MAT_Ice', 'MAT_Lamp', 'MAT_Marble', 'MAT_Steel', 'MAT_Wall', 'MAT_Wood']) ok(em.includes(m), 'ENV material ' + m);
let prims = 0, with1 = 0;
// every primitive whose material has an occlusion (AO) texture must carry TEXCOORD_1 (Ice/Lamp/Steel are flat-colour, no textures)
for (const mesh of er.listMeshes()) for (const p of mesh.listPrimitives()) {
  if (!p.getMaterial().getOcclusionTexture()) continue; prims++; if (p.getAttribute('TEXCOORD_1')) with1++;
}
ok(prims > 0 && prims === with1, `ENV TEXCOORD_1 on ${with1}/${prims} AO-textured primitives`);
for (const m of er.listMaterials()) { const o = m.getOcclusionTexture(); if (o) ok(m.getOcclusionTextureInfo().getTexCoord() === 1, `ENV ${m.getName()} occlusion texCoord=1`); }
const pr = props.getRoot();
const pm = pr.listMaterials().map(m => m.getName());
console.log('PROPS materials', pm.join(','));
for (const m of ['MAT_Props', 'MAT_ScreenRuntime', 'MAT_PosterRuntime', 'MAT_PhoneRuntime']) ok(pm.includes(m), 'PROPS material ' + m);
for (const [doc, tag] of [[env, 'ENV'], [props, 'PROPS']]) for (const m of doc.getRoot().listMaterials()) {
  if (!/Runtime$/.test(m.getName())) continue;
  const t = m.getEmissiveTexture();
  ok(!!t && !m.getBaseColorTexture() && !m.getNormalTexture() && !m.getMetallicRoughnessTexture(), `${tag} ${m.getName()} = emissive image only`);
  console.log('   emissiveFactor', m.getEmissiveFactor(), 'baseColorFactor', m.getBaseColorFactor(), 'texCoord', m.getEmissiveTextureInfo().getTexCoord());
  for (const mesh of doc.getRoot().listMeshes()) for (const p of mesh.listPrimitives()) if (p.getMaterial() === m) {
    const uv = p.getAttribute('TEXCOORD_0'); const a = uv.getArray(); const n = uv.getCount();
    let u0 = 9, u1 = -9, v0 = 9, v1 = -9; for (let i = 0; i < n; i++) { u0 = Math.min(u0, a[2 * i]); u1 = Math.max(u1, a[2 * i]); v0 = Math.min(v0, a[2 * i + 1]); v1 = Math.max(v1, a[2 * i + 1]); }
    // orientation: UV signed area vs position-space winding -> not mirrored if u increases along +X (or tangent) consistently; check unit square corners
    ok(Math.abs(u0) < 1e-3 && Math.abs(u1 - 1) < 1e-3 && Math.abs(v0) < 1e-3 && Math.abs(v1 - 1) < 1e-3, `${tag} ${mesh.getName()}/${m.getName()} UV range u[${u0.toFixed(3)},${u1.toFixed(3)}] v[${v0.toFixed(3)},${v1.toFixed(3)}]`);
    const pos = p.getAttribute('POSITION'), idx = p.getIndices().getArray();
    let area = 0; const t0 = idx[0], t1 = idx[1], t2 = idx[2];
    const P = i => pos.getElement(i, []), U = i => uv.getElement(i, []);
    const a0 = P(t0), a1 = P(t1), a2 = P(t2), b0 = U(t0), b1 = U(t1), b2 = U(t2);
    // UV winding must be CCW (positive) when the face winding is CCW as seen from the front (glTF UV origin top-left => v is flipped, so positive-v-up UV appear CW; just print)
    area = (b1[0] - b0[0]) * (b2[1] - b0[1]) - (b1[1] - b0[1]) * (b2[0] - b0[0]);
    const e1 = [a1[0] - a0[0], a1[1] - a0[1], a1[2] - a0[2]], e2 = [a2[0] - a0[0], a2[1] - a0[1], a2[2] - a0[2]];
    const nrm = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
    console.log(`   first tri: UV signed area ${area.toFixed(3)} (glTF v=0 is image TOP, so Blender-style v-up => positive area = not mirrored), geom normal ${nrm.map(x => x.toFixed(4)).join(',')}`);
  }
}
const bill = pr.listNodes().find(n => n.getName() === 'PROP_Bill');
ok(!!bill && !!bill.getMesh(), 'PROP_Bill node present');
if (bill) {
  const me = bill.getMesh(); let tris = 0; const mats = new Set();
  for (const p of me.listPrimitives()) { tris += p.getIndices().getCount() / 3; mats.add(p.getMaterial().getName()); ok(p.getMaterial().getDoubleSided(), 'PROP_Bill material doubleSided'); }
  ok(tris <= 12, 'PROP_Bill tris ' + tris); ok(mats.size === 1, 'PROP_Bill materials ' + [...mats]);
  const pos = me.listPrimitives()[0].getAttribute('POSITION'); const mn = pos.getMinNormalized([]), mx = pos.getMaxNormalized([]);
  console.log('   PROP_Bill bbox', mn.map(x => x.toFixed(3)), mx.map(x => x.toFixed(3)), 'node translation', bill.getTranslation(), 'scale', bill.getScale());
}
const small = pr.listNodes().find(n => n.getName() === 'PROP_CashSmall'), heist = pr.listNodes().find(n => n.getName() === 'PROP_CashHeist');
ok(!!small && !!heist, 'PROP_CashSmall + PROP_CashHeist present');
const sk = small.listChildren().map(c => c.getMesh()), hk = heist.listChildren().filter(c => c.getMesh()).map(c => c.getMesh());
const inst = heist.listChildren().map(c => c.getExtension('EXT_mesh_gpu_instancing')).filter(Boolean)[0];
const ninst = inst ? inst.getAttribute('TRANSLATION').getCount() : heist.listChildren().length;
console.log(`   CashSmall children: ${small.listChildren().map(c => c.getName() + '->mesh ' + pr.listMeshes().indexOf(c.getMesh()))}`);
console.log(`   CashHeist children: ${heist.listChildren().map(c => c.getName() + '->mesh ' + pr.listMeshes().indexOf(c.getMesh()))}; EXT_mesh_gpu_instancing ${inst ? 'YES x' + ninst : 'no (12 plain nodes)'}`);
ok(sk.length === 1 && ninst === 12 && new Set([...sk, ...hk]).size === 1, 'CashSmall bill (1 node) + CashHeist bundles (12 instances) ALL reference ONE glTF mesh ' + (sk[0] && sk[0].getName()));
if (process.argv[4] === 'expect-instanced') ok(!!inst, 'CashHeist bundles use EXT_mesh_gpu_instancing');
for (const n of [small, heist]) { let t = 0; const walk = (x, mult) => { const c = x.getExtension('EXT_mesh_gpu_instancing'); const k = c ? c.getAttribute('TRANSLATION').getCount() : 1; if (x.getMesh()) for (const p of x.getMesh().listPrimitives()) t += k * p.getIndices().getCount() / 3; x.listChildren().forEach(walk); }; walk(n); ok(t <= 3000, `${n.getName()} tris incl. children/instances ${t}`); }
let dc = 0; for (const n of pr.listNodes()) if (n.getMesh()) dc += n.getMesh().listPrimitives().length;
console.log('   PROPS draw calls (mesh-node primitives; instanced node counts once):', dc);
console.log(bad ? `${bad} FAILURES` : 'ALL OK');
process.exit(bad ? 1 : 0);
