// usage: node measure_slide.mjs <glb> [Walk=1.2,Run=3.0,Sneak=0.8] [--scan]
// Foot-slide metric: in-place clips, root moves forward (+Z in glTF) at v m/s. Sole points (heel, ball, tip) are rigid points on Foot / ToeBase bones,
// defined at rest pose (flat on ground). A point is "planted" when its world height < 3 cm.
import { loadGLB } from '../../scripts/glbload.mjs';
import * as THREE from 'three';
const file = process.argv[2];
const spd = { Walk: 1.2, Run: 3.0, Sneak: 0.8 };
if (process.argv[3] && !process.argv[3].startsWith('--')) for (const kv of process.argv[3].split(',')) { const [k, v] = kv.split('='); spd[k] = parseFloat(v); }
const scan = process.argv.includes('--scan');
const g = await loadGLB(file);
const scene = g.scene; scene.updateMatrixWorld(true);
const bone = n => scene.getObjectByName(n);
const wp = o => new THREE.Vector3().setFromMatrixPosition(o.matrixWorld);
const sides = ['Left', 'Right'];
const pts = {}; // side -> [{bone, local:Vector3, name}]
for (const s of sides) {
  const foot = bone(`mixamorig${s}Foot`), toe = bone(`mixamorig${s}ToeBase`);
  const a = wp(foot), t = wp(toe);
  const defs = [['heel', foot, new THREE.Vector3(a.x, a.y, 0.0)], ['ball', toe, new THREE.Vector3(t.x, t.y, 0.0)], ['tip', toe, new THREE.Vector3(t.x, t.y, 0.0)]];
  // rest orientation is Y-up here: height axis is Y, forward is +Z
  const heel = new THREE.Vector3(a.x, 0, a.z - 0.05), ball = new THREE.Vector3(t.x, 0, t.z), tip = new THREE.Vector3(t.x, 0, t.z + 0.07);
  pts[s] = [['heel', foot, heel], ['ball', toe, ball], ['tip', toe, tip]].map(([n, b, p]) => ({ n, b, l: p.clone().applyMatrix4(b.matrixWorld.clone().invert()) }));
  console.log(s, 'rest ankle', a.toArray().map(x => +x.toFixed(3)), 'toe', t.toArray().map(x => +x.toFixed(3)));
}
function sample(clipName) {
  const clip = g.animations.find(c => c.name === clipName);
  const mixer = new THREE.AnimationMixer(scene);
  const act = mixer.clipAction(clip); act.play();
  const N = Math.round(clip.duration * 30) + 1;
  const fr = [];
  for (let k = 0; k < N; k++) {
    mixer.setTime(k / 30); scene.updateMatrixWorld(true);
    const o = {};
    for (const s of sides) o[s] = pts[s].map(p => p.l.clone().applyMatrix4(p.b.matrixWorld));
    fr.push(o);
  }
  return { fr, dur: clip.duration, N };
}
const THR = 0.03;
function analyse(name, v, d) {
  const { fr, N } = d;
  let maxEx = 0, sumEx = 0, nPh = 0, maxV = 0, sumV = 0, nV = 0, minH = 1e9, floatSum = 0, floatN = 0, noContact = 0;
  const phases = [];
  for (const s of sides) for (let pi = 0; pi < 3; pi++) {
    let run = [];
    const flush = () => {
      if (run.length >= 3) {
        const zs = run.map(k => fr[k][s][pi].z + v * k / 30);
        const ex = (Math.max(...zs) - Math.min(...zs)) * 100;
        phases.push({ s, p: pi, f0: run[0], f1: run[run.length - 1], ex });
        maxEx = Math.max(maxEx, ex); sumEx += ex; nPh++;
        for (let i = 1; i < run.length; i++) { const rv = Math.abs((zs[i] - zs[i - 1]) * 30) * 100; maxV = Math.max(maxV, rv); sumV += rv; nV++; }
      }
      run = [];
    };
    for (let k = 0; k < N; k++) {
      const p = fr[k][s][pi];
      minH = Math.min(minH, p.y);
      if (p.y < THR) { run.push(k); floatSum += p.y; floatN++; } else flush();
    }
    flush();
  }
  for (let k = 0; k < N; k++) { let any = false; for (const s of sides) for (const p of fr[k][s]) if (p.y < THR) any = true; if (!any) noContact++; }
  console.log(`${name} v=${v} m/s  stance phases=${nPh}  slide excursion/phase cm: max=${maxEx.toFixed(1)} mean=${(sumEx / Math.max(1, nPh)).toFixed(1)} | residual vel cm/s: max=${maxV.toFixed(1)} mean=${(sumV / Math.max(1, nV)).toFixed(1)} | min sole height=${(minH * 100).toFixed(1)}cm  mean planted height=${(floatSum / Math.max(1, floatN) * 100).toFixed(2)}cm  frames w/o contact=${noContact}/${N}`);
  return phases;
}
for (const name of ['Walk', 'Run', 'Sneak']) {
  const d = sample('Heister_' + name);
  console.log(`-- Heister_${name}: ${d.N} samples, duration ${d.dur.toFixed(3)}s`);
  analyse(name, spd[name], d);
  if (scan) {
    // best-fit speed: mean of -dz/dt over planted samples
    let sum = 0, n = 0;
    for (const s of sides) for (let pi = 0; pi < 3; pi++) for (let k = 1; k < d.N; k++) {
      const a = d.fr[k - 1][s][pi], b = d.fr[k][s][pi];
      if (a.y < THR && b.y < THR) { sum += -(b.z - a.z) * 30; n++; }
    }
    console.log(`   best-fit ground speed from planted samples: ${(sum / Math.max(1, n)).toFixed(2)} m/s (n=${n})`);
    for (const t of [0.6, 0.8, 1.0, 1.2, 1.4, 2, 2.5, 3, 3.5, 4]) { if (Math.abs(t - spd[name]) > 2) continue; }
  }
}


