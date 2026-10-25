// usage: node inspect_glb.mjs file.glb  -> prints node->mesh index, mesh prims/tris, materials, extras checks (raw JSON, no deps)
import fs from 'fs';
const b = fs.readFileSync(process.argv[2]);
const jl = b.readUInt32LE(12);
const j = JSON.parse(b.slice(20, 20 + jl).toString());
const tris = (m) => m.primitives.reduce((s, p) => s + (p.indices !== undefined ? j.accessors[p.indices].count / 3 : 0), 0);
console.log('extensionsUsed', j.extensionsUsed, 'required', j.extensionsRequired);
console.log('nodes:');
j.nodes.forEach((n, i) => console.log(' ', i, n.name, n.mesh !== undefined ? 'mesh#' + n.mesh + ' (' + j.meshes[n.mesh].name + ', tris ' + tris(j.meshes[n.mesh]) + ')' : '(empty/no mesh)', n.extensions ? JSON.stringify(n.extensions).slice(0, 120) : ''));
console.log('meshes:', j.meshes.length, 'materials:');
j.materials.forEach((m, i) => console.log(' ', i, m.name, 'doubleSided=' + !!m.doubleSided, m.occlusionTexture ? 'occ.texCoord=' + (m.occlusionTexture.texCoord || 0) : ''));
console.log('prims:');
j.meshes.forEach((m, i) => m.primitives.forEach((p) => console.log(' mesh', i, m.name, 'mat', j.materials[p.material]?.name, 'attrs', Object.keys(p.attributes).join(','))));
