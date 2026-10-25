// usage: node check_doors.mjs <PROPS-like.glb> [CHAR_Sentinel.glb]
import * as THREE from 'three';
import { loadGLB } from '../../scripts/glbload.mjs';
const [propsFile, sentFile] = process.argv.slice(2);
const deg = r => (r * 180 / Math.PI).toFixed(2);
const g = await loadGLB(propsFile);
console.log('clips:', g.animations.map(a => `${a.name}(${a.duration.toFixed(3)}s,${a.tracks.length}trk)`).join(' '));
let bad = 0;
for (const k of ['L', 'M', 'R']) {
  const door = `VAULT_${k}_Door`;
  const node = g.scene.getObjectByName(door);
  console.log(`${door}: isMesh=${node.isMesh} children=${node.children.length} restRotZ?=${deg(node.rotation.y)}deg(y) restQuat=${node.quaternion.toArray().map(x => x.toFixed(4))} pos=${node.position.toArray().map(x => x.toFixed(2))}`);
  if (!node.isMesh || node.children.length) { bad++; console.log('  FAIL: not a single mesh node'); }
  const rest = new THREE.Vector3(); const restBox = new THREE.Box3().setFromObject(node);
  for (const cname of ['VaultDoor_Open', 'VaultDoor_Slam', `${door}_Open`, `${door}_Slam`, `${door}_Ajar`]) {
    const clip = g.animations.find(a => a.name === cname);
    if (!clip) { if (!cname.endsWith('Ajar') || k === 'L') { bad++; console.log('  MISSING', cname); } continue; }
    const targets = new Set(clip.tracks.map(t => t.name.split('.')[0]));
    const own = targets.has(door);
    const shared = cname.startsWith('VaultDoor_');
    const okTargets = shared ? targets.size === 3 : (targets.size === 1 && own);
    const mixer = new THREE.AnimationMixer(g.scene);
    const act = mixer.clipAction(clip); act.play();
    const samp = t => { mixer.setTime(t); g.scene.updateMatrixWorld(true);
      const hinge = new THREE.Vector3().setFromMatrixPosition(node.matrixWorld);
      const c = new THREE.Box3().setFromObject(node).getCenter(new THREE.Vector3());
      // a vertex-ish probe: the mesh bbox centre, expressed relative to the hinge in XZ(world)-plane radius
      return { hinge, c, r: Math.hypot(c.x - hinge.x, c.z - hinge.z), yaw: Math.atan2(c.x - hinge.x, c.z - hinge.z) }; };
    const T = clip.duration;
    const a = samp(0), m = samp(T * 0.5), z = samp(T - 1e-4);
    const hing = Math.max(a.hinge.distanceTo(m.hinge), a.hinge.distanceTo(z.hinge));
    const cm = a.c.distanceTo(z.c), cmid = a.c.distanceTo(m.c);
    // how the visible mesh orbits the hinge: radius stays ~const (world bbox of a rotating disc grows, so only report)
    console.log(`  ${cname}: tracksOn=[${[...targets]}] ok=${okTargets} hingeMoved=${hing.toFixed(4)} meshCenterMoved(start->end)=${cm.toFixed(3)} (start->mid)=${cmid.toFixed(3)} yaw start/mid/end=${deg(a.yaw)}/${deg(m.yaw)}/${deg(z.yaw)}`);
    if (!okTargets || hing > 0.01) bad++;
    if (!cname.endsWith('Ajar') && cmid < 0.05) { bad++; console.log('   FAIL mesh does not move'); }
    mixer.stopAllAction(); mixer.uncacheRoot(g.scene);
    node.position.set(...node.position.toArray());
  }
}
console.log(bad ? `DOOR CHECK: ${bad} problem(s)` : 'DOOR CHECK: OK');
if (sentFile) {
  const s = await loadGLB(sentFile);
  const n = s.scene.getObjectByName('CHAR_Sentinel');
  let skinned = 0; s.scene.traverse(o => { if (o.isSkinnedMesh || o.isBone) skinned++; });
  const meshes = []; s.scene.traverse(o => o.isMesh && meshes.push(o.name));
  console.log(`Sentinel: isMesh=${n.isMesh} children=${n.children.length} meshes=[${meshes}] skinnedOrBones=${skinned}`);
  for (const a of s.animations) console.log('  ', a.name, a.duration.toFixed(3) + 's', [...new Set(a.tracks.map(t => t.name))].join(','));
}
