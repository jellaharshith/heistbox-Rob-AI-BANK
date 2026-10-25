import fs from 'fs';
import path from 'path';
import validator from 'gltf-validator';

const dir = process.argv[2] || 'export';
let bad = 0;
for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.glb')).sort()) {
  const p = path.join(dir, f);
  const r = await validator.validateBytes(new Uint8Array(fs.readFileSync(p)), { uri: f, maxIssues: 200 });
  const i = r.issues;
  console.log(`${f}: errors=${i.numErrors} warnings=${i.numWarnings} infos=${i.numInfos} hints=${i.numHints}`);
  const seen = new Map();
  for (const m of i.messages.filter(m => m.severity <= 1)) {
    const k = `${m.severity === 0 ? 'ERROR' : 'WARN'} ${m.code}`;
    if (!seen.has(k)) seen.set(k, []);
    seen.get(k).push(m.pointer + ' - ' + m.message);
  }
  for (const [k, v] of seen) console.log(`  ${k} x${v.length}: ${v[0]}`);
  if (i.numErrors) bad++;
}
process.exit(bad ? 1 : 0);
