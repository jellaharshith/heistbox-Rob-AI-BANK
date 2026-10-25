// Contact sheet: node scripts/sheet.mjs out.png cols cellW cellH img1.png img2.png ...
import sharp from 'sharp';
const [out, cols, cw, ch, ...files] = process.argv.slice(2);
const C = +cols, W = +cw, H = +ch, rows = Math.ceil(files.length / C);
const comps = [];
for (let i = 0; i < files.length; i++) {
  const buf = await sharp(files[i]).resize(W, H, { fit: 'contain', background: '#15171c' }).toBuffer();
  comps.push({ input: buf, left: (i % C) * W, top: Math.floor(i / C) * H });
}
await sharp({ create: { width: W * C, height: H * rows, channels: 3, background: '#15171c' } }).composite(comps).png().toFile(out);
console.log('sheet', out);
