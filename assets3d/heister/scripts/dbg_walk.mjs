import { loadGLB } from '../../scripts/glbload.mjs';
import * as THREE from 'three';
const g = await loadGLB(process.argv[2]);
const clipName = process.argv[3] || 'Heister_Walk';
const sc = g.scene;
const c = g.animations.find(c => c.name === clipName);
for (const t of c.tracks) if (/Hips|LeftFoot|LeftUpLeg/.test(t.name)) console.log(t.name, t.times.length, t.times[0], t.times[t.times.length - 1]);
const m = new THREE.AnimationMixer(sc); m.clipAction(c).play();
const N = Math.round(c.duration * 30) + 1;
for (let k = 0; k < N; k += 1) {
  m.setTime(k / 30); sc.updateMatrixWorld(true);
  const p = n => new THREE.Vector3().setFromMatrixPosition(sc.getObjectByName(n).matrixWorld);
  const lf = p('mixamorigLeftFoot'), rf = p('mixamorigRightFoot'), h = p('mixamorigHips'), lt = p('mixamorigLeftToeBase');
  console.log(k, 'LF', lf.toArray().map(x => (x * 100).toFixed(1)).join(','), 'RF', rf.toArray().map(x => (x * 100).toFixed(1)).join(','), 'hips', h.toArray().map(x => (x * 100).toFixed(1)).join(','), 'LT', lt.toArray().map(x => (x * 100).toFixed(1)).join(','));
}
