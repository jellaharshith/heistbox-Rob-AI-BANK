// Contract load test: loads every export GLB with three.js GLTFLoader + MeshoptDecoder (node), logs node / clip / morph names,
// and FAILS (exit 1) on any missing contract name or unresolvable animation track.
//   node scripts/loadtest.mjs [dir=export] [--quiet]
import path from 'path';
import * as THREE from 'three';
import { loadGLB } from './glbload.mjs';

const dir = process.argv[2] && !process.argv[2].startsWith('--') ? process.argv[2] : 'export';
const quiet = process.argv.includes('--quiet');

const VISEMES = ['viseme_sil','viseme_PP','viseme_FF','viseme_TH','viseme_DD','viseme_kk','viseme_CH','viseme_SS','viseme_nn','viseme_RR','viseme_aa','viseme_E','viseme_I','viseme_O','viseme_U'];
const FACE = [...VISEMES, 'eyeBlinkLeft','eyeBlinkRight','mouthSmile','browUp','browDown','jawOpen'];
const ARKIT_MIN = ['eyeBlinkLeft','eyeBlinkRight','jawOpen','mouthSmile'];

// nodes: must exist by name. morphs: {node: [keys]}. clips/materials: exact names. bones: [min, max] skeleton size (0,0 = none).
const CONTRACT = {
  'CHAR_Tina.glb': {
    nodes: ['CHAR_Tina','CHAR_Tina_LOD0','CHAR_Tina_LOD1','CHAR_Tina_LOD2','CHAR_Tina_Eyes'],
    morphs: { CHAR_Tina_LOD0_1: FACE },
    clips: ['Tina_Idle','Tina_Talk','Tina_Typing','Tina_Approve','Tina_Deny','Tina_Alarm'],
    materials: ['MAT_Tina','MAT_Tina_Seam'], bones: [1, 65], hipsBone: 'mixamorig:Hips',
  },
  'CHAR_Heister.glb': {
    nodes: ['CHAR_Heister','CHAR_Heister_Body_LOD0','CHAR_Heister_Mask_LOD0','CHAR_Heister_Duffel_LOD0'],
    morphs: { CHAR_Heister_Body_LOD0: ARKIT_MIN },
    clips: ['Heister_Idle','Heister_Walk','Heister_Run','Heister_Sneak','Heister_Talk','Heister_Bribe','Heister_Caught','Heister_Celebrate'],
    materials: ['MAT_Heister'], bones: [1, 65], hipsBone: 'mixamorig:Hips',
  },
  'CHAR_Customer.glb': {
    nodes: ['CHAR_Customer','CHAR_Customer_LOD0','PROP_Phone'],
    morphs: { CHAR_Customer_LOD0: ARKIT_MIN },
    clips: ['Customer_Idle','Customer_Wait','Customer_FaceID','Customer_Happy'],
    materials: ['MAT_PhoneRuntime'], bones: [1, 65], hipsBone: 'mixamorig:Hips',
  },
  'CHAR_Sentinel.glb': {
    nodes: ['CHAR_Sentinel'], clips: ['Sentinel_Hover','Sentinel_Scan','Sentinel_Fire'], materials: [], bones: [0, 0],
  },
  'ENV_Bank.glb': {
    nodes: ['SPAWN_Player','SPAWN_Customer','CAM_Overview','CAM_VaultL','CAM_VaultM','CAM_VaultR','ANCHOR_LaserTarget'],
    clips: [], materials: [], bones: [0, 0],
  },
  'PROPS.glb': {
    nodes: ['VAULT_L_Door','VAULT_M_Door','VAULT_R_Door','PROP_Shredder','FX_Laser','PROP_CashSmall','PROP_CashHeist','PROP_Bill','PROP_Megaphone',
            'PROP_WantedPoster','PROP_Terminal','PROP_Phone','FX_LockdownStrip_L','FX_LockdownStrip_M','FX_LockdownStrip_R'],
    clips: ['VaultDoor_Open','VaultDoor_Slam',
            'VAULT_L_Door_Open','VAULT_L_Door_Slam','VAULT_L_Door_Ajar','VAULT_M_Door_Open','VAULT_M_Door_Slam','VAULT_R_Door_Open','VAULT_R_Door_Slam'],
    materials: ['MAT_PosterRuntime','MAT_ScreenRuntime','MAT_PhoneRuntime'], bones: [0, 0],
  },
};

const fails = [];
const miss = (file, what) => { fails.push(`${file}: ${what}`); console.log(`  !! MISSING ${what}`); };
const names = o => { const s = new Set(); o.traverse(n => n.name && s.add(n.name)); return s; };

for (const [file, c] of Object.entries(CONTRACT)) {
  const p = path.join(dir, file);
  let g;
  try { g = await loadGLB(p); } catch (e) { fails.push(`${file}: LOAD FAILED ${e.message}`); console.log(`${file}: LOAD FAILED ${e.message}`); continue; }
  console.log(`== ${file}`);
  const all = names(g.scene);
  const mats = new Set(); const skinned = []; let bones = 0;
  g.scene.traverse(o => {
    if (o.isMesh) (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => m.name && mats.add(m.name));
    if (o.isSkinnedMesh) { skinned.push(o); bones = Math.max(bones, o.skeleton.bones.length); }
  });
  if (!quiet) {
    console.log('  nodes: ' + [...all].filter(n => !n.startsWith('mixamorig')).join(', '));
    console.log('  clips: ' + g.animations.map(a => a.name).join(', '));
    console.log('  materials: ' + [...mats].join(', '));
    const mt = new Map();
    skinned.concat([]).forEach(m => m.morphTargetDictionary && mt.set(m.name, Object.keys(m.morphTargetDictionary)));
    g.scene.traverse(o => { if (o.isMesh && o.morphTargetDictionary) mt.set(o.name, Object.keys(o.morphTargetDictionary)); });
    for (const [n, k] of mt) console.log(`  morphs ${n}: ${k.join(' ')}`);
    console.log(`  bones: ${bones}`);
  }
  for (const n of c.nodes) if (!all.has(n)) miss(file, `node ${n}`);
  for (const a of c.clips) if (!g.animations.some(x => x.name === a)) miss(file, `clip ${a}`);
  for (const m of c.materials) if (!mats.has(m)) miss(file, `material ${m}`);
  for (const [n, keys] of Object.entries(c.morphs || {})) {
    let node = null; g.scene.traverse(o => { if (o.name === n && !node) node = o; });
    const dict = node && (node.morphTargetDictionary || (node.children.find(ch => ch.morphTargetDictionary) || {}).morphTargetDictionary);
    if (!dict) { miss(file, `morph dictionary on ${n}`); continue; }
    for (const k of keys) if (!(k in dict)) miss(file, `morph ${k} on ${n}`);
  }
  if (bones < c.bones[0] || bones > c.bones[1]) miss(file, `bone count ${bones} outside [${c.bones}]`);
  // three.js strips ':' from node names, so compare sanitized
  if (c.hipsBone && !all.has(THREE.PropertyBinding.sanitizeNodeName(c.hipsBone))) miss(file, `bone ${c.hipsBone}`);
  // skinned meshes must actually render where their skeleton is (guards against quantization/skin-transform bugs in the optimizer)
  if (skinned.length) {
    g.scene.updateMatrixWorld(true);
    const bb = new THREE.Box3(), v = new THREE.Vector3(); g.scene.traverse(o => o.isBone && bb.expandByPoint(o.getWorldPosition(v)));
    for (const m of skinned.filter(m => /LOD0$|LOD0_\d+$|^CHAR_\w+_(Body|Mask|Eyes?L?R?)$|^CHAR_Customer_LOD0$/.test(m.name) || !/LOD\d/.test(m.name))) {
      m.skeleton.update(); const box = new THREE.Box3().setFromObject(m, true);
      const ok = box.min.y > bb.min.y - 0.25 && box.max.y > bb.max.y - 0.3 && box.max.y < bb.max.y + 0.6;
      if (!quiet) console.log(`  skin ${m.name}: mesh y ${box.min.y.toFixed(2)}..${box.max.y.toFixed(2)} vs bones y ${bb.min.y.toFixed(2)}..${bb.max.y.toFixed(2)}`);
      if (!ok) miss(file, `skinned mesh ${m.name} renders at y ${box.min.y.toFixed(2)}..${box.max.y.toFixed(2)} but skeleton spans ${bb.min.y.toFixed(2)}..${bb.max.y.toFixed(2)} (bad skin/quantization)`);
    }
  }
  // every animation track must bind to a real node (and morph tracks to a real key)
  for (const a of g.animations) for (const t of a.tracks) {
    const pb = THREE.PropertyBinding.parseTrackName(t.name);
    const node = THREE.PropertyBinding.findNode(g.scene, pb.nodeName);
    if (!node) { miss(file, `track target ${t.name} (clip ${a.name})`); break; }
  }
}

// Vault door pivot check: the named node must carry the clip and the visible mesh must swing around the hinge.
try {
  const g = await loadGLB(path.join(dir, 'PROPS.glb'));
  for (const door of ['VAULT_L_Door','VAULT_M_Door','VAULT_R_Door']) {
    const node = g.scene.getObjectByName(door);
    if (!node) continue;
    const meshes = []; node.traverse(o => o.isMesh && meshes.push(o));
    if (!meshes.length) { miss('PROPS.glb', `visible mesh under ${door}`); continue; }
    const clip = g.animations.find(a => a.name === `${door}_Open`) || g.animations.find(a => a.name === 'VaultDoor_Open');
    if (!clip) continue;
    const mixer = new THREE.AnimationMixer(g.scene);
    const act = mixer.clipAction(clip); act.play();
    const sample = t => { mixer.setTime(t); g.scene.updateMatrixWorld(true);
      const hinge = new THREE.Vector3().setFromMatrixPosition(node.matrixWorld);
      const box = new THREE.Box3(); meshes.forEach(m => box.expandByObject(m));
      return { hinge, center: box.getCenter(new THREE.Vector3()) }; };
    const a0 = sample(clip.tracks[0].times[0]), a1 = sample(clip.duration - 1e-4); // LoopRepeat would wrap t=duration back to 0
    const hingeMoved = a0.hinge.distanceTo(a1.hinge), meshMoved = a0.center.distanceTo(a1.center);
    const tracksOnNode = clip.tracks.filter(t => t.name.startsWith(door + '.') || t.name.startsWith(node.uuid)).length;
    console.log(`  door ${door} (${clip.name}): hingeMoved=${hingeMoved.toFixed(3)}m meshCenterMoved=${meshMoved.toFixed(3)}m tracksOnNamedNode=${tracksOnNode}`);
    if (hingeMoved > 0.01) miss('PROPS.glb', `${door} hinge translates (${hingeMoved.toFixed(3)}m) - pivot is not on the hinge`);
    if (meshMoved < 0.05) miss('PROPS.glb', `${door} visible mesh does not move when ${clip.name} plays`);
    if (!tracksOnNode) miss('PROPS.glb', `${door} named node carries no track in ${clip.name}`);
    mixer.stopAllAction(); mixer.uncacheRoot(g.scene);
  }
} catch (e) { fails.push('vault pivot check failed: ' + e.message); }

console.log(fails.length ? `\nLOADTEST FAILED: ${fails.length} problem(s)\n - ` + fails.join('\n - ') : '\nLOADTEST OK: every contract name present');
process.exit(fails.length ? 1 : 0);



