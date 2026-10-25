// Splits the exporter's merged AO+ORM texture: occlusion -> Hall_AO.png on TEXCOORD_1, metalRough -> ORM png on TEXCOORD_0
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { prune } from '@gltf-transform/functions';
import fs from 'fs';
const ENV = 'C:/Users/Shaik/Downloads/heistbox/assets3d/env';
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const doc = await io.read(ENV + '/export/ENV_Bank.glb');
const ao = doc.createTexture('Hall_AO').setImage(new Uint8Array(fs.readFileSync(ENV + '/textures/Hall_AO.png'))).setMimeType('image/png');
for (const m of doc.getRoot().listMaterials()) {
  const k = m.getName().replace('MAT_', '');
  const p = `${ENV}/textures/${k}_ORM.png`;
  if (!fs.existsSync(p)) continue;
  const orm = doc.createTexture(k + '_ORM').setImage(new Uint8Array(fs.readFileSync(p))).setMimeType('image/png');
  m.setMetallicRoughnessTexture(orm); m.getMetallicRoughnessTextureInfo().setTexCoord(0);
  m.setOcclusionTexture(ao); m.getOcclusionTextureInfo().setTexCoord(1);
  m.getBaseColorTextureInfo().setTexCoord(0);
  m.getNormalTextureInfo().setTexCoord(0);
}
await doc.transform(prune({ keepLeaves: true }));
await io.write(ENV + '/export/ENV_Bank.glb', doc);
console.log('fixed');
