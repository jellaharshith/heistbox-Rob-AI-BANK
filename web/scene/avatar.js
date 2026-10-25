/**
 * HeistBox 3D Scene - In-memory Avatar Placeholder Generator
 * Pure client-side Canvas rendering - Zero network calls.
 */

import * as THREE from './three.module.js';

let cachedAvatarCanvas = null;

export function getAvatarCanvas() {
  if (cachedAvatarCanvas) return cachedAvatarCanvas;

  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext('2d');

  // 1. Dark booking lineup background
  const bgGrad = ctx.createLinearGradient(0, 0, 0, 512);
  bgGrad.addColorStop(0, '#0F172A');
  bgGrad.addColorStop(1, '#020617');
  ctx.fillStyle = bgGrad;
  ctx.fillRect(0, 0, 512, 512);

  // 2. Police Lineup Grid & Height Measurement Lines
  ctx.strokeStyle = 'rgba(71, 85, 105, 0.4)';
  ctx.lineWidth = 2;
  ctx.fillStyle = '#64748B';
  ctx.font = 'bold 16px monospace';

  const heights = [
    { y: 80, label: '6\'6"' },
    { y: 135, label: '6\'0"' },
    { y: 190, label: '5\'6"' },
    { y: 245, label: '5\'0"' },
    { y: 300, label: '4\'6"' },
    { y: 355, label: '4\'0"' },
  ];

  heights.forEach(h => {
    ctx.beginPath();
    ctx.moveTo(40, h.y);
    ctx.lineTo(472, h.y);
    ctx.stroke();

    ctx.textAlign = 'left';
    ctx.fillText(h.label, 12, h.y + 5);
    ctx.textAlign = 'right';
    ctx.fillText(h.label, 500, h.y + 5);
  });

  // Vertical center guide
  ctx.strokeStyle = 'rgba(71, 85, 105, 0.2)';
  ctx.beginPath();
  ctx.moveTo(256, 40);
  ctx.lineTo(256, 420);
  ctx.stroke();

  // 3. Mystery Suspect Silhouette
  ctx.fillStyle = '#1E293B';
  // Torso / shoulders
  ctx.beginPath();
  ctx.ellipse(256, 450, 150, 110, 0, Math.PI, 0, false);
  ctx.fill();

  // Neck
  ctx.fillRect(234, 300, 44, 50);

  // Head
  ctx.beginPath();
  ctx.ellipse(256, 240, 75, 90, 0, 0, Math.PI * 2);
  ctx.fill();

  // Mask / Shades
  ctx.fillStyle = '#0F172A';
  ctx.fillRect(205, 215, 102, 32);

  // Visor / Lens glow
  ctx.fillStyle = '#FACC15';
  ctx.fillRect(215, 225, 36, 12);
  ctx.fillRect(261, 225, 36, 12);

  // Suspect Question Mark
  ctx.fillStyle = 'rgba(250, 204, 21, 0.85)';
  ctx.font = '900 68px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('?', 256, 160);

  // 4. Booking ID Banner at Bottom
  ctx.fillStyle = '#020617';
  ctx.fillRect(0, 420, 512, 92);
  ctx.strokeStyle = '#FACC15';
  ctx.lineWidth = 4;
  ctx.strokeRect(4, 424, 504, 84);

  ctx.fillStyle = '#FACC15';
  ctx.font = '900 24px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('SUSPECT: UNIDENTIFIED', 256, 452);

  ctx.fillStyle = '#94A3B8';
  ctx.font = 'bold 15px monospace';
  ctx.fillText('HEISTBOX ARCHIVE • CASE #4975-PAIR', 256, 484);

  cachedAvatarCanvas = canvas;
  return canvas;
}

export function createAvatarTexture() {
  const canvas = getAvatarCanvas();
  const tex = new THREE.CanvasTexture(canvas);
  tex.needsUpdate = true;
  return tex;
}
