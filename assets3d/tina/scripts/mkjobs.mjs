// node mkjobs.mjs <glb> <outDir> <set> -> writes <outDir>/jobs_<set>.json (batch for scripts/shot.mjs)
import fs from 'fs';
const [glb, out, set] = process.argv.slice(2);
const V = 'viseme_sil viseme_PP viseme_FF viseme_TH viseme_DD viseme_kk viseme_CH viseme_SS viseme_nn viseme_RR viseme_aa viseme_E viseme_I viseme_O viseme_U'.split(' ');
const jobs = [];
const add = (name, o) => jobs.push({ src: glb, out: `${out}/${name}.png`, ...o });
if (set === 'vis') {
  for (const v of V) add('vis_' + v, { view: 'head', morph: v + ':1', size: '400x400' });
  for (const v of ['viseme_PP', 'viseme_FF', 'viseme_aa', 'viseme_O', 'viseme_U']) add('vis3q_' + v, { view: 'head3q', morph: v + ':1', size: '400x400' });
}
if (set === 'face') {
  add('head_rest', { view: 'head', size: '600x600' });
  add('head3q_rest', { view: 'head3q', size: '600x600' });
  add('headside_rest', { view: 'headside', size: '600x600' });
  for (const m of ['jawOpen:1', 'viseme_aa:1', 'viseme_O:1', 'eyeBlinkLeft:1,eyeBlinkRight:1', 'mouthSmile:1']) add('head_' + m.split(':')[0], { view: 'head', morph: m, size: '600x600' });
  add('head3q_jawOpen', { view: 'head3q', morph: 'jawOpen:1', size: '600x600' });
  add('head3q_aa', { view: 'head3q', morph: 'viseme_aa:1', size: '600x600' });
}
if (set === 'body') {
  add('front', { view: 'front', pose: 'rest', size: '640x800' });
  add('3q', { view: '3q', clip: 'Tina_Idle', t: 0, size: '640x800' });
  add('head', { view: 'head', clip: 'Tina_Idle', t: 0, size: '640x640' });
  add('head3q', { view: 'head3q', clip: 'Tina_Idle', t: 0, size: '640x640' });
}
if (set === 'clips') {
  const T = { Tina_Alarm: [0.3, 0.8, 1.4], Tina_Approve: [0.9, 1.4, 1.9], Tina_Deny: [0.9, 1.4, 1.9] };
  for (const [c, ts] of Object.entries(T)) for (const t of ts) for (const view of ['upper', 'front']) add(`${c}_${t}_${view}`, { clip: c, t, view, size: '480x560' });
}
fs.mkdirSync(out, { recursive: true });
fs.writeFileSync(`${out}/jobs_${set}.json`, JSON.stringify(jobs, null, 1));
console.log(jobs.length, 'jobs');
