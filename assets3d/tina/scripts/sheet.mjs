// node sheet.mjs out.png cols cell crop(x,y,w,h|none) file1 file2 ...   (label = file base name) contact sheet via sharp
import sharp from 'sharp';
import path from 'path';
const [out, colsS, cellS, cropS, ...files] = process.argv.slice(2);
const cols = +colsS, cell = +cellS, rows = Math.ceil(files.length / cols);
const comps = [];
for (let i = 0; i < files.length; i++) {
  let im = sharp(files[i]);
  if (cropS !== 'none') { const [x, y, w, h] = cropS.split(',').map(Number); im = im.extract({ left: x, top: y, width: w, height: h }); }
  const buf = await im.resize(cell, cell, { fit: 'cover' }).toBuffer();
  const label = path.basename(files[i], '.png');
  const svg = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${cell}" height="22"><rect width="100%" height="22" fill="#000" fill-opacity=".6"/><text x="6" y="16" font-size="14" fill="#fff" font-family="Arial">${label}</text></svg>`);
  comps.push({ input: buf, left: (i % cols) * cell, top: Math.floor(i / cols) * cell }, { input: svg, left: (i % cols) * cell, top: Math.floor(i / cols) * cell });
}
await sharp({ create: { width: cols * cell, height: rows * cell, channels: 3, background: '#111' } }).composite(comps).png().toFile(out);
console.log('wrote', out);
