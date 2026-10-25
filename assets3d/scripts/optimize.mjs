// Pack optimizer (replaces `gltf-transform optimize`, whose KHR_mesh_quantization step mis-scales SKINNED meshes in three.js:
// the dequantize node-transform is ignored for skinned nodes, so characters render ~0.6 m low/shrunk; it also splits every mesh
// onto an unnamed child node of the named node).  Here:  prune(keepLeaves) -> reorder -> webp textures -> EXT_meshopt_compression
// with the FILTER/QUANTIZE method only (filters decode to float32 in the decoder, no KHR_mesh_quantization, no extra nodes).
// Nothing is flattened / joined / palettised / instanced / simplified, so empties, node names, material names and UV1 (AO) survive.
//   node scripts/optimize.mjs in.glb out.glb [--texture-size 1024]
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS, EXTMeshoptCompression } from '@gltf-transform/extensions';
import { prune, reorder, textureCompress } from '@gltf-transform/functions';
import { MeshoptEncoder, MeshoptDecoder } from 'meshoptimizer';
import sharp from 'sharp';
import fs from 'fs';

const [src, dst] = process.argv.slice(2, 4);
const ti = process.argv.indexOf('--texture-size');
const texSize = ti > 0 ? +process.argv[ti + 1] : null;
await MeshoptEncoder.ready; await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });
const doc = await io.read(src);
doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({ method: EXTMeshoptCompression.EncoderMethod.QUANTIZE });
await doc.transform(
  prune({ keepLeaves: true, keepAttributes: true, keepExtras: true, keepIndices: true }),
  reorder({ encoder: MeshoptEncoder }),
  textureCompress({ encoder: sharp, targetFormat: 'webp', ...(texSize ? { resize: [texSize, texSize] } : {}) }),
);
await io.write(dst, doc);
console.log(`optimized ${src} -> ${dst}: ${(fs.statSync(src).size / 1048576).toFixed(2)} MB -> ${(fs.statSync(dst).size / 1048576).toFixed(2)} MB`);
