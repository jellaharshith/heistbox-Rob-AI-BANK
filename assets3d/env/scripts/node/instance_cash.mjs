// Post-process (run after the Blender merge/export, which cannot write EXT_mesh_gpu_instancing):
// collapses the 12 child nodes PROP_CashHeist_Bundle.NN (all sharing mesh CASH_Bundle) into ONE node "PROP_CashHeist_Bundles"
// with EXT_mesh_gpu_instancing (TRANSLATION/ROTATION/SCALE per instance) so the crate costs 2 draw calls, not 13.
// PROP_CashSmall_Bill keeps referencing the same CASH_Bundle mesh as a plain node.  Idempotent.
//   node instance_cash.mjs in.glb out.glb
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS, EXTMeshGPUInstancing } from '@gltf-transform/extensions';
const [src, dst] = process.argv.slice(2, 4);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const doc = await io.read(src);
const root = doc.getRoot();
const crate = root.listNodes().find(n => n.getName() === 'PROP_CashHeist');
const kids = crate.listChildren().filter(n => n.getName().startsWith('PROP_CashHeist_Bundle') && n.getName() !== 'PROP_CashHeist_Bundles' && n.getMesh());
if (kids.length) {
  const mesh = kids[0].getMesh();
  if (!kids.every(k => k.getMesh() === mesh)) throw new Error('bundle nodes do not share one mesh');
  const N = kids.length, buf = root.listBuffers()[0];
  const T = new Float32Array(N * 3), R = new Float32Array(N * 4), S = new Float32Array(N * 3);
  kids.forEach((k, i) => { T.set(k.getTranslation(), i * 3); R.set(k.getRotation(), i * 4); S.set(k.getScale(), i * 3); });
  const acc = (arr, type, name) => doc.createAccessor(name).setType(type).setArray(arr).setBuffer(buf);
  const ext = doc.createExtension(EXTMeshGPUInstancing).setRequired(false);
  const inst = ext.createInstancedMesh()
    .setAttribute('TRANSLATION', acc(T, 'VEC3', 'inst_T')).setAttribute('ROTATION', acc(R, 'VEC4', 'inst_R')).setAttribute('SCALE', acc(S, 'VEC3', 'inst_S'));
  const node = doc.createNode('PROP_CashHeist_Bundles').setMesh(mesh).setExtension('EXT_mesh_gpu_instancing', inst);
  crate.addChild(node);
  kids.forEach(k => { crate.removeChild(k); k.dispose(); });
  console.log(`instanced ${N} bundle nodes -> PROP_CashHeist_Bundles (mesh ${mesh.getName()})`);
} else console.log('no bundle child nodes to instance (already done?)');
await io.write(dst, doc);
