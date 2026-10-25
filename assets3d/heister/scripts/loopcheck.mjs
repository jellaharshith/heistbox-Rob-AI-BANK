import { loadGLB } from '../../scripts/glbload.mjs';
import * as THREE from 'three';
const g = await loadGLB(process.argv[2]);
const sc = g.scene;
const names = ['mixamorigLeftFoot', 'mixamorigRightHand', 'mixamorigHips'];
for (const c of g.animations) {
  const m = new THREE.AnimationMixer(sc); const a = m.clipAction(c); a.play();
  const N = Math.round(c.duration * 30) + 1;
  const P = k => { m.setTime(k / 30); sc.updateMatrixWorld(true); return names.map(n => new THREE.Vector3().setFromMatrixPosition(sc.getObjectByName(n).matrixWorld)); };
  const p0 = P(0), pl = P(N - 1), pl1 = P(N - 2);
  const d = (a, b) => Math.max(...a.map((x, i) => x.distanceTo(b[i]))) * 100;
  const tr = c.tracks.find(t => t.name.includes('Hips.position') || t.name.includes('Hips.quaternion'));
  console.log(c.name.padEnd(18), 'dur', c.duration.toFixed(3), 'samples', N, 'first-last cm', d(p0, pl).toFixed(2), 'last-1 vs last cm', d(pl1, pl).toFixed(2), 'times', tr ? tr.times[0].toFixed(3) + '..' + tr.times[tr.times.length - 1].toFixed(3) : '');
}
