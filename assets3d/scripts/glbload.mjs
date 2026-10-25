import fs from 'fs';
import path from 'path';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';

// Node has no image decoding and textures are irrelevant to the structural checks: drop texture refs from the JSON chunk.
function stripTextures(buf) {
  const jsonLen = buf.readUInt32LE(12);
  const json = JSON.parse(buf.subarray(20, 20 + jsonLen).toString('utf8'));
  delete json.textures; delete json.images; delete json.samplers;
  const strip = o => { if (o && typeof o === 'object') for (const k of Object.keys(o)) { if (/Texture$/.test(k) && o[k] && 'index' in o[k]) delete o[k]; else strip(o[k]); } };
  strip(json.materials);
  json.extensionsUsed = (json.extensionsUsed || []).filter(e => !/texture/i.test(e));
  json.extensionsRequired = (json.extensionsRequired || []).filter(e => !/texture/i.test(e));
  let j = Buffer.from(JSON.stringify(json), 'utf8');
  j = Buffer.concat([j, Buffer.alloc((4 - (j.length % 4)) % 4, 0x20)]);
  const rest = buf.subarray(20 + jsonLen);
  const out = Buffer.concat([Buffer.alloc(20), j, rest]);
  out.writeUInt32LE(0x46546C67, 0); out.writeUInt32LE(2, 4); out.writeUInt32LE(out.length, 8);
  out.writeUInt32LE(j.length, 12); out.writeUInt32LE(0x4E4F534A, 16);
  return out;
}

export async function loadGLB(file) {
  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  const buf = stripTextures(fs.readFileSync(file));
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  return new Promise((res, rej) => loader.parse(ab, '', res, rej));
}


