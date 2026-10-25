import { loadGLB } from '../../scripts/glbload.mjs';
const g = await loadGLB(process.argv[2]);
for (const c of g.animations) { const ends = {}; for (const t of c.tracks) { const e = t.times[t.times.length-1].toFixed(3); ends[e] = (ends[e]||0)+1; } console.log(c.name, c.duration.toFixed(3), JSON.stringify(ends)); }
