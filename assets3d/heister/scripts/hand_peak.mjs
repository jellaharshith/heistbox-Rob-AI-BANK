import { loadGLB } from '../../scripts/glbload.mjs';
import * as THREE from 'three';
const g = await loadGLB(process.argv[2]); const sc = g.scene;
const c = g.animations.find(c => c.name === (process.argv[3]||'Heister_Bribe'));
const m = new THREE.AnimationMixer(sc); m.clipAction(c).play();
const N = Math.round(c.duration*30)+1; let best = {R:[-1,0],L:[-1,0]};
const p = n => new THREE.Vector3().setFromMatrixPosition(sc.getObjectByName(n).matrixWorld);
let rows=[];
for (let k=0;k<N;k++){ m.setTime(k/30); sc.updateMatrixWorld(true); const r=p('mixamorigRightHand'), l=p('mixamorigLeftHand'), h=p('mixamorigHips'), hd=p('mixamorigHead');
 if (r.y>best.R[0]) best.R=[r.y,k,r.z-h.z]; if (l.y>best.L[0]) best.L=[l.y,k,l.z-h.z];
 if(k%5==0) rows.push(`${k}: R y=${r.y.toFixed(3)} fwd=${(r.z-h.z).toFixed(2)}  L y=${l.y.toFixed(3)} fwd=${(l.z-h.z).toFixed(2)}`);}
console.log(rows.join('\n')); console.log('peak R y/frame/fwd', best.R.map(x=>+x.toFixed(3)), 'peak L', best.L.map(x=>+x.toFixed(3)));
