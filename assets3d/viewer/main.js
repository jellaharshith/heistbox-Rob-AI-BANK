import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

// Query: ?src=/CHAR_Tina.glb (served from export/) or /@fs/<abs path>.glb ; &clip=Name&t=0.5 ; &view=front|side|3q|head|back|top ; &morph=viseme_PP:1,jawOpen:0.4
const q = new URLSearchParams(location.search);
const FILES = ['CHAR_Tina','CHAR_Heister','CHAR_Customer','CHAR_Sentinel','ENV_Bank','PROPS'];
const canvas = document.getElementById('c'), ui = document.getElementById('ui');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
const scene = new THREE.Scene(); scene.background = new THREE.Color(0x2b303a);
scene.add(new THREE.HemisphereLight(0xdde8ff, 0x403830, 1.6));
const key = new THREE.DirectionalLight(0xffffff, 2.4); key.position.set(-2, 4, -3); scene.add(key); // key from the character's front (-Y in Blender = +Z... see views)
const fill = new THREE.DirectionalLight(0x9fc8ff, 1.0); fill.position.set(3, 2, 3); scene.add(fill);
scene.add(new THREE.GridHelper(10, 20, 0x556, 0x334));
const camera = new THREE.PerspectiveCamera(35, 1, 0.01, 200);
const controls = new OrbitControls(camera, canvas);
const loader = new GLTFLoader(); loader.setMeshoptDecoder(MeshoptDecoder);

const rest = new Map();
let gltf, mixer, actions = {}, current = null, root, lodMeshes = {}, morphMeshes = [], bbox = new THREE.Box3();
const api = window.__viewer = { ready: false };

function resize() { const w = innerWidth, h = innerHeight; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); }
addEventListener('resize', resize); resize();

function view(name) {
  const c = bbox.getCenter(new THREE.Vector3()), s = bbox.getSize(new THREE.Vector3());
  const R = Math.max(s.x, s.y, s.z) * 1.25 + 0.3;
  let target = c.clone(), dir = new THREE.Vector3(0, 0.1, 1), dist = R * 1.6;
  if (name === 'side') dir.set(1, 0.1, 0); else if (name === 'back') dir.set(0, 0.1, -1);
  else if (name === '3q') dir.set(0.8, 0.25, 0.8); else if (name === 'top') dir.set(0, 1, 0.01);
  else if (name === 'head' || name === 'headside' || name === 'head3q') { // character heads: top 12% of the bbox
    target = new THREE.Vector3(c.x, bbox.max.y - s.y * 0.07, c.z); dist = s.y * 0.45;
    if (name === 'headside') dir.set(1, 0.05, 0); if (name === 'head3q') dir.set(0.6, 0.1, 0.8);
  } else if (name === 'upper') { target = new THREE.Vector3(c.x, bbox.max.y - s.y * 0.3, c.z); dist = s.y * 1.0; }
  dir.normalize(); camera.position.copy(target).addScaledVector(dir, dist); controls.target.copy(target); controls.update();
}
api.view = view;

function setClip(name, t) {
  if (current) { current.stop(); current = null; }
  mixer.stopAllAction();
  if (!name) { resetPose(); return; }
  const clip = gltf.animations.find(a => a.name === name); if (!clip) throw new Error('no clip ' + name);
  const a = mixer.clipAction(clip); a.setLoop(THREE.LoopRepeat); a.play(); current = a; api.clip = name;
  if (t !== undefined) { mixer.setTime(Math.min(t, clip.duration - 1e-3)); a.paused = true; } // sample first: a paused action is not evaluated by setTime
  else a.paused = false;
  refreshBounds();
}
api.setClip = setClip;
function resetPose() { // rest pose = the node TRS stored in the glTF (skeleton.pose() ignores armature parent transforms, so don't use it)
  mixer.stopAllAction(); mixer.uncacheRoot(gltf.scene); api.clip = null; current = null;
  rest.forEach((r, o) => { o.position.copy(r.p); o.quaternion.copy(r.q); o.scale.copy(r.s); }); gltf.scene.updateMatrixWorld(true); refreshBounds();
}
api.pose = resetPose;
function setMorph(name, v) { morphMeshes.forEach(m => { const i = m.morphTargetDictionary[name]; if (i !== undefined) m.morphTargetInfluences[i] = v; }); }
api.setMorph = setMorph;
api.clearMorphs = () => morphMeshes.forEach(m => m.morphTargetInfluences.fill(0));
api.showLOD = n => Object.entries(lodMeshes).forEach(([k, arr]) => arr.forEach(o => o.visible = (n === 'all' || k === String(n))));
api.hide = names => gltf.scene.traverse(o => { if (names.includes(o.name)) o.visible = false; });
function refreshBounds() { // skinned meshes: three's SkinnedMesh.computeBoundingBox applies the current bone pose
  gltf.scene.updateMatrixWorld(true); bbox.makeEmpty();
  const b = new THREE.Box3();
  gltf.scene.traverse(o => {
    if (!o.isMesh || !o.visible || /_LOD[12]/.test(o.name) || /_LOD[12]/.test(o.parent?.name || '')) return;
    if (o.isSkinnedMesh) { o.skeleton.update(); bbox.union(b.makeEmpty().setFromObject(o, true)); }
    else bbox.expandByObject(o);
  });
  if (bbox.isEmpty()) bbox.setFromObject(gltf.scene);
}
function buildUI() {
  ui.innerHTML = '';
  const sel = document.createElement('select'); sel.id = 'sel';
  FILES.forEach(f => sel.add(new Option(f, `/${f}.glb`))); sel.onchange = () => { q.set('src', sel.value); location.search = q.toString(); };
  if (![...sel.options].some(o => o.value === q.get('src'))) sel.add(new Option(q.get('src'), q.get('src')));
  sel.value = q.get('src'); ui.append(sel);
  const sec = (t) => { const h = document.createElement('h4'); h.textContent = t; ui.append(h); };
  sec('Clips');
  const b0 = document.createElement('button'); b0.textContent = 'T-pose / rest'; b0.onclick = () => setClip(null); ui.append(b0);
  gltf.animations.forEach(a => { const b = document.createElement('button'); b.textContent = a.name; b.onclick = () => { [...ui.querySelectorAll('button')].forEach(x => x.classList.remove('on')); b.classList.add('on'); setClip(a.name); }; ui.append(b); });
  sec('Views'); ['front','side','back','3q','head','headside','head3q','upper','top'].forEach(v => { const b = document.createElement('button'); b.textContent = v; b.onclick = () => view(v); ui.append(b); });
  if (Object.keys(lodMeshes).length) { sec('LOD'); ['all', ...Object.keys(lodMeshes)].forEach(k => { const b = document.createElement('button'); b.textContent = k === 'all' ? 'all' : 'LOD' + k; b.onclick = () => api.showLOD(k); ui.append(b); }); }
  const dict = morphMeshes[0]?.morphTargetDictionary;
  if (dict) { sec('Morph targets'); const r = document.createElement('button'); r.textContent = 'reset'; r.onclick = () => { api.clearMorphs(); ui.querySelectorAll('input').forEach(i => i.value = 0); }; ui.append(r);
    Object.keys(dict).forEach(k => { const l = document.createElement('label'); const i = document.createElement('input'); i.type = 'range'; i.min = 0; i.max = 1; i.step = 0.01; i.value = 0; i.oninput = () => setMorph(k, +i.value); l.append(k, i); ui.append(l); }); }
}

const src = q.get('src') || '/CHAR_Tina.glb';
loader.load(src, g => {
  gltf = g; scene.add(g.scene); g.scene.traverse(o => rest.set(o, { p: o.position.clone(), q: o.quaternion.clone(), s: o.scale.clone() })); mixer = new THREE.AnimationMixer(g.scene);
  g.scene.traverse(o => {
    const m = /_LOD(\d)/.exec(o.name); if (m && o.isMesh || (m && o.type === 'Group')) { (lodMeshes[m[1]] ||= []).push(o); }
    if (o.isMesh && o.morphTargetDictionary) morphMeshes.push(o);
    if (o.isMesh) (Array.isArray(o.material) ? o.material : [o.material]).forEach(mm => { if (mm.alphaTest) mm.alphaTest = mm.alphaTest; });
  });
  // show LOD0 only by default (LODs overlap)
  if (lodMeshes[0]) Object.entries(lodMeshes).forEach(([k, arr]) => arr.forEach(o => { if (k !== '0') o.visible = false; }));
  refreshBounds(); view(q.get('view') || '3q');
  buildUI();
  if (q.get('clip')) setClip(q.get('clip'), q.has('t') ? +q.get('t') : undefined);
  else if (q.get('pose') === 'rest') resetPose();
  (q.get('morph') || '').split(',').filter(Boolean).forEach(p => { const [k, v] = p.split(':'); setMorph(k, +v); });
  if (q.get('hide')) api.hide(q.get('hide').split(','));
  api.gltf = g; api.camera = camera; api.bbox = bbox; api.mixer = mixer; api.ready = true;
}, undefined, e => { document.title = 'ERROR ' + e.message; console.error(e); api.error = String(e); });

const clock = new THREE.Clock();
renderer.setAnimationLoop(() => { const dt = clock.getDelta(); if (mixer && current && !current.paused) mixer.update(dt); controls.update(); renderer.render(scene, camera); });





