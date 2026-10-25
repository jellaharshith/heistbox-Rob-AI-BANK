import { loadGLB } from '../../scripts/glbload.mjs';
import * as THREE from 'three';
const g = await loadGLB(process.argv[2]); const sc = g.scene;
const eff = o => { for (let n = o; n; n = n.parent) if (!n.visible) return false; return true; };
const meshes = []; sc.traverse(o => { if (o.isMesh || o.isSkinnedMesh) meshes.push(o); });
const state = () => Object.fromEntries(meshes.map(m => [m.name, eff(m)]));
const grp = n => sc.getObjectByName(n);
for (const n of ['CHAR_Heister_Mask', 'CHAR_Heister_Duffel']) {
  const e = grp(n); console.log(n, 'type', e.type, 'children', e.children.map(c => c.name + (c.isSkinnedMesh ? '(skinned)' : '')).join(','), 'parent', e.parent.name);
  console.log('  local matrix identity:', e.matrix.equals(new THREE.Matrix4()), ' pos', e.position.toArray().map(x => +x.toFixed(3)));
}
const names = k => Object.entries(state()).filter(([n, v]) => v === k).map(([n]) => n);
const part = p => meshes.filter(m => m.name.startsWith('CHAR_Heister_' + p + '_LOD')).map(m => m.name);
let ok = true; const chk = (c, msg) => { console.log((c ? 'PASS ' : 'FAIL ') + msg); if (!c) ok = false; };
const all = state();
chk(Object.values(all).every(v => v), 'all meshes visible by default (' + meshes.length + ' meshes)');
grp('CHAR_Heister_Mask').visible = false;
let s = state();
chk(part('Mask').length === 3 && part('Mask').every(n => !s[n]), 'hide Mask group -> ' + part('Mask').join(',') + ' invisible');
chk(['Body', 'Duffel', 'EyeL', 'EyeR'].every(p => part(p).length === 3 && part(p).every(n => s[n])), 'Body/Duffel/Eyes still visible');
grp('CHAR_Heister_Mask').visible = true;
grp('CHAR_Heister_Duffel').visible = false;
s = state();
chk(part('Duffel').length === 3 && part('Duffel').every(n => !s[n]), 'hide Duffel group -> ' + part('Duffel').join(',') + ' invisible');
chk(['Body', 'Mask', 'EyeL', 'EyeR'].every(p => part(p).every(n => s[n])), 'Body/Mask/Eyes still visible');
grp('CHAR_Heister_Duffel').visible = true;
chk(Object.values(state()).every(v => v), 'restored');
// duffel follows the spine during Run
const c = g.animations.find(c => c.name === 'Heister_Run');
const m = new THREE.AnimationMixer(sc); m.clipAction(c).play();
const d = sc.getObjectByName('CHAR_Heister_Duffel_LOD0'); const pts = [];
for (let k = 0; k < 25; k++) { m.setTime(k / 30); sc.updateMatrixWorld(true); const bb = new THREE.Box3().setFromObject(d); pts.push(bb.getCenter(new THREE.Vector3())); }
const mn = pts.reduce((a, p) => a.min(p), new THREE.Vector3(1e9, 1e9, 1e9)), mx = pts.reduce((a, p) => a.max(p), new THREE.Vector3(-1e9, -1e9, -1e9));
console.log('duffel LOD0 world position range during Run (cm):', mx.clone().sub(mn).multiplyScalar(100).toArray().map(x => +x.toFixed(1)), 'first', pts[0].toArray().map(x => +x.toFixed(3)), 'frame6', pts[6].toArray().map(x => +x.toFixed(3)));
chk(mx.clone().sub(mn).length() > 0.01, 'duffel world position changes with Heister_Run');
// parent chain of duffel -> spine bone
const chain = []; for (let n = d; n; n = n.parent) chain.push(n.name); console.log('duffel chain', chain.join(' < '));
// hips vs duffel relative-distance constant (rigid on spine)
const sp = sc.getObjectByName('mixamorigSpine');
const rel = []; for (const k of [0, 6, 12, 18]) { m.setTime(k / 30); sc.updateMatrixWorld(true); const bb = new THREE.Box3().setFromObject(d).getCenter(new THREE.Vector3()); const q = sp.getWorldQuaternion(new THREE.Quaternion()).invert(); rel.push(bb.sub(new THREE.Vector3().setFromMatrixPosition(sp.matrixWorld)).applyQuaternion(q)); }
console.log('duffel in spine frame (should be constant):', rel.map(v => v.toArray().map(x => +x.toFixed(3)).join(',')).join(' | '));
console.log(ok ? 'ALL PASS' : 'SOME FAIL');
