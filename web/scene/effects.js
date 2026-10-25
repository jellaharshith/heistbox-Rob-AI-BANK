/**
 * HeistBox 3D Scene - Environment Effects, Weather & Time of Day
 * - Weather Modes: Clear Night, Rain, Fog, Sandstorm
 * - Animated Day/Night Cycle (setTimeOfDay)
 * - Camera Screen Shake
 * - 3D BUSTED Stamp overlay
 */

import * as THREE from './three.module.js';
import * as audio from './audio.js';
import { getAvatarCanvas } from './avatar.js';

export class EffectsManager {
  constructor(scene, renderer, camera) {
    this.scene = scene;
    this.renderer = renderer;
    this.camera = camera;

    this.weatherMode = 'Clear Night';
    this.timeOfDay = 0.0; // 0.0 = midnight, 0.25 = sunrise, 0.5 = noon, 0.75 = sunset
    this.shakeIntensity = 0;
    this.isLowQuality = false;

    this.initLights();
    this.initStars();
    this.initRain();
    this.initSandstorm();
    this.initBustedStamp();
    this.initOverlays();

    this.setWeather('Clear Night');
    this.setTimeOfDay(0.0);
  }

  setLowQuality(isLow) {
    this.isLowQuality = Boolean(isLow);
  }

  initOverlays() {
    if (typeof document === 'undefined') return;

    if (!document.getElementById('heistbox-card-styles')) {
      const style = document.createElement('style');
      style.id = 'heistbox-card-styles';
      style.textContent = `
        @keyframes gtaCardSlam {
          0% { transform: scale(1.5); opacity: 0; filter: blur(8px); }
          45% { transform: scale(0.97); opacity: 1; filter: blur(0); }
          75% { transform: scale(1.02); }
          100% { transform: scale(1.0); opacity: 1; }
        }
        @keyframes coinBounce {
          0%, 100% { transform: translateY(0) rotate(0deg); }
          50% { transform: translateY(-12px) rotate(180deg); }
        }
        .heistbox-card-backdrop {
          position: fixed;
          inset: 0;
          background: rgba(7, 10, 22, 0.78);
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          pointer-events: auto;
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 9999;
          animation: fadeIn 0.2s ease-out;
        }
        .heistbox-gta-card {
          position: relative;
          width: 90vw;
          max-width: 420px;
          background: linear-gradient(175deg, #131B2E 0%, #090D18 100%);
          border: 2px solid #EF4444;
          border-radius: 16px;
          box-shadow: 0 0 45px rgba(239, 68, 68, 0.45), 0 20px 50px rgba(0, 0, 0, 0.85);
          padding: 20px 22px;
          color: #F8FAFC;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          box-sizing: border-box;
          animation: gtaCardSlam 0.4s cubic-bezier(0.12, 0.95, 0.2, 1) forwards;
          text-align: center;
        }
        .heistbox-gta-card.robbed-mode {
          border-color: #EAB308;
          box-shadow: 0 0 45px rgba(234, 179, 8, 0.45), 0 20px 50px rgba(0, 0, 0, 0.85);
        }
        .gta-banner {
          font-size: 38px;
          font-weight: 900;
          letter-spacing: 4px;
          text-transform: uppercase;
          text-align: center;
          padding: 8px 14px;
          border-radius: 8px;
          margin-bottom: 14px;
          transform: rotate(-1.5deg);
        }
        .gta-busted-banner {
          background: #EF4444;
          color: #FFFFFF;
          box-shadow: 0 6px 20px rgba(239, 68, 68, 0.6);
          text-shadow: 0 2px 4px rgba(0,0,0,0.6);
        }
        .gta-robbed-banner {
          background: #EAB308;
          color: #090D18;
          box-shadow: 0 6px 20px rgba(234, 179, 8, 0.6);
          text-shadow: none;
        }
        .card-dept-header {
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 2px;
          font-weight: 800;
          color: #94A3B8;
          margin-bottom: 8px;
        }
        .card-photo-box {
          position: relative;
          width: 200px;
          height: 200px;
          margin: 0 auto 14px;
          border-radius: 12px;
          overflow: hidden;
          border: 2px solid rgba(255, 255, 255, 0.2);
          background: #000;
          box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.8);
        }
        .card-photo-canvas {
          width: 100%;
          height: 100%;
          display: block;
          object-fit: cover;
        }
        .card-latency-badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: rgba(239, 68, 68, 0.18);
          border: 1px solid #EF4444;
          color: #FCA5A5;
          padding: 6px 14px;
          border-radius: 9999px;
          font-size: 13px;
          font-weight: 800;
          letter-spacing: 0.5px;
          margin-bottom: 12px;
        }
        .card-latency-badge.robbed-badge {
          background: rgba(234, 179, 8, 0.18);
          border-color: #EAB308;
          color: #FDE047;
        }
        .card-stat-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
          text-align: left;
          background: rgba(15, 23, 42, 0.65);
          border: 1px solid rgba(255, 255, 255, 0.08);
          padding: 10px 12px;
          border-radius: 8px;
          font-size: 11px;
          margin-bottom: 12px;
        }
        .card-stat-grid strong {
          color: #F8FAFC;
          font-size: 12px;
          display: block;
        }
        .card-stat-grid span {
          color: #64748B;
          text-transform: uppercase;
          font-size: 9px;
          letter-spacing: 0.5px;
        }
        .card-dismiss-tip {
          font-size: 10px;
          color: rgba(255, 255, 255, 0.4);
          text-transform: uppercase;
          letter-spacing: 1px;
        }
        .coin-icon-float {
          position: absolute;
          font-size: 26px;
          animation: coinBounce 1.6s ease-in-out infinite;
          filter: drop-shadow(0 4px 8px rgba(0,0,0,0.5));
        }
        @media (max-width: 480px) {
          .heistbox-gta-card {
            max-width: 340px;
            padding: 16px 16px;
          }
          .gta-banner {
            font-size: 30px;
            padding: 6px 10px;
            margin-bottom: 10px;
          }
          .card-photo-box {
            width: 160px;
            height: 160px;
            margin-bottom: 10px;
          }
          .card-latency-badge {
            font-size: 11px;
            padding: 4px 10px;
          }
          .card-stat-grid {
            padding: 8px 10px;
            font-size: 10px;
          }
        }
      `;
      document.head.appendChild(style);
    }

    // Flash overlay
    if (!document.getElementById('heistbox-flash-overlay')) {
      const flash = document.createElement('div');
      flash.id = 'heistbox-flash-overlay';
      flash.style.cssText = 'position:fixed;inset:0;background:#ffffff;opacity:0;pointer-events:none;z-index:10000;';
      document.body.appendChild(flash);
    }
  }

  initLights() {
    // Ambient light
    this.ambientLight = new THREE.AmbientLight(0x1E293B, 1.2);
    this.scene.add(this.ambientLight);

    // Directional Sun / Moon
    this.sunLight = new THREE.DirectionalLight(0xFFFBEB, 2.2);
    this.sunLight.position.set(40, 65, 40);
    this.sunLight.castShadow = true;
    this.sunLight.shadow.mapSize.width = 2048;
    this.sunLight.shadow.mapSize.height = 2048;
    this.sunLight.shadow.camera.near = 10;
    this.sunLight.shadow.camera.far = 160;
    this.sunLight.shadow.camera.left = -60;
    this.sunLight.shadow.camera.right = 60;
    this.sunLight.shadow.camera.top = 60;
    this.sunLight.shadow.camera.bottom = -60;
    this.sunLight.shadow.bias = -0.0005;
    this.scene.add(this.sunLight);

    // Hemisphere sky bounce
    this.hemiLight = new THREE.HemisphereLight(0x38BDF8, 0x0B0F1E, 0.8);
    this.scene.add(this.hemiLight);
  }

  initStars() {
    const starCount = 350;
    const starGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(starCount * 3);

    for (let i = 0; i < starCount; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(Math.random() * 0.8 + 0.2); // Upper hemisphere
      const rad = 110 + Math.random() * 20;

      positions[i * 3] = rad * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = rad * Math.cos(phi);
      positions[i * 3 + 2] = rad * Math.sin(phi) * Math.sin(theta);
    }

    starGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const starMat = new THREE.PointsMaterial({
      color: 0xFFFBEB,
      size: 0.8,
      transparent: true,
      opacity: 0.85,
    });

    this.starField = new THREE.Points(starGeo, starMat);
    this.scene.add(this.starField);
  }

  initRain() {
    this.rainCount = 800;
    const rainGeo = new THREE.BoxGeometry(0.04, 1.4, 0.04);
    const rainMat = new THREE.MeshBasicMaterial({
      color: 0xBAE6FD,
      transparent: true,
      opacity: 0.6,
    });

    this.rainMesh = new THREE.InstancedMesh(rainGeo, rainMat, this.rainCount);
    this.rainParticles = [];

    const dummy = new THREE.Object3D();
    for (let i = 0; i < this.rainCount; i++) {
      const p = {
        x: (Math.random() - 0.5) * 120,
        y: Math.random() * 50 + 2,
        z: (Math.random() - 0.5) * 120,
        speed: 35 + Math.random() * 15,
      };
      this.rainParticles.push(p);

      dummy.position.set(p.x, p.y, p.z);
      dummy.rotation.z = 0.12; // Wind slant
      dummy.updateMatrix();
      this.rainMesh.setMatrixAt(i, dummy.matrix);
    }

    this.rainMesh.visible = false;
    this.scene.add(this.rainMesh);
  }

  initSandstorm() {
    this.sandCount = 600;
    const sandGeo = new THREE.BoxGeometry(0.12, 0.08, 0.12);
    const sandMat = new THREE.MeshBasicMaterial({
      color: 0xFBBF24,
      transparent: true,
      opacity: 0.65,
    });

    this.sandMesh = new THREE.InstancedMesh(sandGeo, sandMat, this.sandCount);
    this.sandParticles = [];

    const dummy = new THREE.Object3D();
    for (let i = 0; i < this.sandCount; i++) {
      const p = {
        x: (Math.random() - 0.5) * 130,
        y: Math.random() * 25 + 0.5,
        z: (Math.random() - 0.5) * 130,
        speedX: 25 + Math.random() * 20,
        speedZ: (Math.random() - 0.5) * 8,
      };
      this.sandParticles.push(p);

      dummy.position.set(p.x, p.y, p.z);
      dummy.updateMatrix();
      this.sandMesh.setMatrixAt(i, dummy.matrix);
    }

    this.sandMesh.visible = false;
    this.scene.add(this.sandMesh);
  }

  initBustedStamp() {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 256;
    const ctx = canvas.getContext('2d');

    // Distress stamp border
    ctx.strokeStyle = '#EF4444';
    ctx.lineWidth = 16;
    ctx.strokeRect(16, 16, 480, 224);

    ctx.fillStyle = '#EF4444';
    ctx.font = '900 84px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('BUSTED', 256, 110);

    ctx.font = 'bold 26px monospace';
    ctx.fillText('PAIR KERNEL LOCKED', 256, 178);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, depthTest: false, transparent: true, opacity: 0 });
    this.bustedSprite = new THREE.Sprite(spriteMat);
    this.bustedSprite.scale.set(16, 8, 1);
    this.bustedSprite.position.set(0, 14, 0);
    this.bustedSprite.visible = false;
    this.scene.add(this.bustedSprite);
  }

  showBustedStamp(durationMs = 2800) {
    this.bustedSprite.visible = true;
    this.bustedSprite.material.opacity = 1.0;
    this.bustedSprite.scale.set(24, 12, 1); // Slam impact scale down

    // Position dead-center in front of camera
    const dir = new THREE.Vector3();
    this.camera.getWorldDirection(dir);
    this.bustedSprite.position.copy(this.camera.position).addScaledVector(dir, 20);

    this.shakeCamera(0.85);

    const t0 = performance.now();
    const anim = () => {
      const elapsed = (performance.now() - t0) / 1000;
      if (elapsed < 0.25) {
        // Slam zoom in
        const s = THREE.MathUtils.lerp(24, 16, elapsed / 0.25);
        this.bustedSprite.scale.set(s, s * 0.5, 1);
        requestAnimationFrame(anim);
      } else if (elapsed < durationMs / 1000) {
        requestAnimationFrame(anim);
      } else {
        // Fade out
        const fade = (elapsed - durationMs / 1000) / 0.5;
        if (fade < 1.0) {
          this.bustedSprite.material.opacity = 1.0 - fade;
          requestAnimationFrame(anim);
        } else {
          this.bustedSprite.visible = false;
        }
      }
    };
    anim();
  }

  shakeCamera(intensity = 0.5) {
    this.shakeIntensity = intensity;
  }

  flashCamera() {
    if (this.isLowQuality) return;
    const overlay = document.getElementById('heistbox-flash-overlay');
    if (overlay) {
      overlay.style.transition = 'none';
      overlay.style.opacity = '0.94';
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          overlay.style.transition = 'opacity 0.45s cubic-bezier(0.1, 0.9, 0.2, 1)';
          overlay.style.opacity = '0';
        });
      });
    }

    // Bloom exposure flash
    const origExp = this.renderer.toneMappingExposure || 1.1;
    this.renderer.toneMappingExposure = origExp * 2.4;
    const t0 = performance.now();
    const restore = () => {
      const elapsed = performance.now() - t0;
      if (elapsed < 420) {
        this.renderer.toneMappingExposure = THREE.MathUtils.lerp(origExp * 2.4, origExp, elapsed / 420);
        requestAnimationFrame(restore);
      } else {
        this.renderer.toneMappingExposure = origExp;
      }
    };
    requestAnimationFrame(restore);
  }

  dismissCards() {
    const existing = document.getElementById('heistbox-active-card-modal');
    if (existing) {
      existing.remove();
    }
  }

  showBustedCard({ photoBitmap = null, latencyMs = 0.8, onDismiss = null } = {}) {
    this.dismissCards();

    // 1. Flash effect & camera shutter sound
    this.flashCamera();
    audio.playCameraShutter();
    this.shakeCamera(0.85);

    // 2. Build Card Modal
    const backdrop = document.createElement('div');
    backdrop.id = 'heistbox-active-card-modal';
    backdrop.className = 'heistbox-card-backdrop';

    const card = document.createElement('div');
    card.className = 'heistbox-gta-card';

    card.innerHTML = `
      <div class="card-dept-header">LAS VEGAS METRO POLICE • BOOKING RECORD</div>
      <div class="gta-banner gta-busted-banner">BUSTED</div>
      <div class="card-photo-box">
        <canvas class="card-photo-canvas" width="220" height="220" id="busted-mugshot-cvs"></canvas>
      </div>
      <div class="card-latency-badge">
        <span>⚡ KERNEL RESPONSE: <strong>${Number(latencyMs).toFixed(1)}ms</strong></span>
      </div>
      <div class="card-stat-grid">
        <div><span>SUSPECT</span><strong>GRANDMA TRICKSTER</strong></div>
        <div><span>VERDICT</span><strong style="color:#EF4444;">AIRLOCK BLOCKED</strong></div>
        <div><span>ATTEMPT</span><strong>$4,975.00 WIRE</strong></div>
        <div><span>SETTLED</span><strong style="color:#10B981;">$0.00 (ROLLED BACK)</strong></div>
      </div>
      <div class="card-dismiss-tip">Tap anywhere to dismiss</div>
    `;

    backdrop.appendChild(card);
    document.body.appendChild(backdrop);

    // Render photo or avatar placeholder on the canvas
    const cvs = document.getElementById('busted-mugshot-cvs');
    if (cvs) {
      const ctx = cvs.getContext('2d');
      if (photoBitmap && typeof photoBitmap.width === 'number') {
        ctx.drawImage(photoBitmap, 0, 0, 220, 220);
      } else {
        const avatarCvs = getAvatarCanvas();
        ctx.drawImage(avatarCvs, 0, 0, 220, 220);
      }
    }

    const closeHandler = () => {
      backdrop.remove();
      if (onDismiss) onDismiss();
    };
    backdrop.addEventListener('click', closeHandler);
  }

  showRobbedCard({ photoBitmap = null, amount = 497500, onDismiss = null } = {}) {
    this.dismissCards();

    // Sound & camera shake
    audio.playCoinShower(20);
    this.shakeCamera(0.5);

    const backdrop = document.createElement('div');
    backdrop.id = 'heistbox-active-card-modal';
    backdrop.className = 'heistbox-card-backdrop';

    const card = document.createElement('div');
    card.className = 'heistbox-gta-card robbed-mode';

    card.innerHTML = `
      <div class="card-dept-header">VAULT SECURITY BREACH • HEIST SUCCESS</div>
      <div class="gta-banner gta-robbed-banner">💰 ROBBED 💰</div>
      <div class="card-photo-box">
        <canvas class="card-photo-canvas" width="220" height="220" id="robbed-mugshot-cvs"></canvas>
        <span class="coin-icon-float" style="top:8px;left:8px;">🪙</span>
        <span class="coin-icon-float" style="top:12px;right:8px;animation-delay:0.4s;">🪙</span>
        <span class="coin-icon-float" style="bottom:8px;right:14px;animation-delay:0.8s;">💰</span>
      </div>
      <div class="card-latency-badge robbed-badge">
        <span>🪙 NAIVE LLM JUDGE: <strong>99.8% TRUSTED</strong></span>
      </div>
      <div class="card-stat-grid">
        <div><span>ATTACKER</span><strong>GRANDMA TRICKSTER</strong></div>
        <div><span>TARGET</span><strong style="color:#EAB308;">LEFT VAULT</strong></div>
        <div><span>DRAINED</span><strong style="color:#EF4444;">$${(amount / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}</strong></div>
        <div><span>DEFENSE</span><strong style="color:#F87171;">PROMPT EXPLOITED</strong></div>
      </div>
      <div class="card-dismiss-tip">Tap anywhere to dismiss</div>
    `;

    backdrop.appendChild(card);
    document.body.appendChild(backdrop);

    const cvs = document.getElementById('robbed-mugshot-cvs');
    if (cvs) {
      const ctx = cvs.getContext('2d');
      if (photoBitmap && typeof photoBitmap.width === 'number') {
        ctx.drawImage(photoBitmap, 0, 0, 220, 220);
      } else {
        const avatarCvs = getAvatarCanvas();
        ctx.drawImage(avatarCvs, 0, 0, 220, 220);
      }
    }

    const closeHandler = () => {
      backdrop.remove();
      if (onDismiss) onDismiss();
    };
    backdrop.addEventListener('click', closeHandler);
  }

  setWeather(mode) {
    const m = (mode || '').toLowerCase().replace(/[\s_-]+/g, '');

    // Reset particles & fog
    this.rainMesh.visible = false;
    this.sandMesh.visible = false;
    this.scene.fog = null;

    if (m === 'clearnight' || m === 'clear') {
      this.weatherMode = 'Clear Night';
      this.currentWeather = 'Clear Night';
      this.renderer.setClearColor(0x0B0F1E);
      this.scene.background = new THREE.Color(0x0B0F1E);
      this.starField.visible = true;
    } else if (m === 'rain') {
      this.weatherMode = 'Rain';
      this.currentWeather = 'Rain';
      this.renderer.setClearColor(0x080C16);
      this.scene.background = new THREE.Color(0x080C16);
      this.scene.fog = new THREE.FogExp2(0x0E1726, 0.015);
      this.rainMesh.visible = true;
      this.starField.visible = false;
    } else if (m === 'fog') {
      this.weatherMode = 'Fog';
      this.currentWeather = 'Fog';
      this.renderer.setClearColor(0x111827);
      this.scene.background = new THREE.Color(0x111827);
      this.scene.fog = new THREE.FogExp2(0x1E293B, 0.012);
      this.starField.visible = false;
    } else if (m === 'sandstorm' || m === 'dust') {
      this.weatherMode = 'Sandstorm';
      this.currentWeather = 'Sandstorm';
      this.renderer.setClearColor(0x78350F);
      this.scene.background = new THREE.Color(0x78350F);
      this.scene.fog = new THREE.FogExp2(0xB45309, 0.024);
      this.sandMesh.visible = true;
      this.starField.visible = false;
    }
  }

  setTimeOfDay(t) {
    this.timeOfDay = t; // 0.0 = midnight, 0.5 = noon

    // Calculate sun arc
    const angle = t * Math.PI * 2;
    const sunY = Math.sin(angle - Math.PI / 2) * 65;
    const sunX = Math.cos(angle - Math.PI / 2) * 65;

    this.sunLight.position.set(sunX, Math.max(10, Math.abs(sunY)), 40);

    const isDay = sunY > 0;
    if (this.weatherMode === 'Clear Night') {
      if (isDay) {
        // Daytime sky
        const skyColor = new THREE.Color(0x38BDF8).lerp(new THREE.Color(0xE0F2FE), (sunY / 65));
        this.scene.background = skyColor;
        this.renderer.setClearColor(skyColor);
        this.ambientLight.intensity = 1.8;
        this.sunLight.intensity = 2.8;
        this.sunLight.color.setHex(0xFFFBEB);
        this.starField.visible = false;
      } else {
        // Midnight sky
        const midnight = new THREE.Color(0x0B0F1E);
        this.scene.background = midnight;
        this.renderer.setClearColor(midnight);
        this.ambientLight.intensity = 1.2;
        this.sunLight.intensity = 1.0;
        this.sunLight.color.setHex(0x94A3B8); // Cool moonlight
        this.starField.visible = true;
      }
    }
  }

  update(delta) {
    // 1. Update Camera Screen Shake
    if (this.shakeIntensity > 0.005) {
      const rx = (Math.random() - 0.5) * this.shakeIntensity * 1.2;
      const ry = (Math.random() - 0.5) * this.shakeIntensity * 1.2;
      const rz = (Math.random() - 0.5) * this.shakeIntensity * 1.2;

      this.camera.position.x += rx;
      this.camera.position.y += ry;
      this.camera.position.z += rz;

      this.shakeIntensity = THREE.MathUtils.lerp(this.shakeIntensity, 0, delta * 8);
    }

    // 2. Update Rain Simulation
    if (this.rainMesh.visible) {
      const dummy = new THREE.Object3D();
      for (let i = 0; i < this.rainCount; i++) {
        const p = this.rainParticles[i];
        p.y -= p.speed * delta;
        p.x -= 4.0 * delta; // Wind slant

        if (p.y < 0.2) {
          p.y = 48 + Math.random() * 4;
          p.x = (Math.random() - 0.5) * 120;
        }

        dummy.position.set(p.x, p.y, p.z);
        dummy.rotation.z = 0.12;
        dummy.updateMatrix();
        this.rainMesh.setMatrixAt(i, dummy.matrix);
      }
      this.rainMesh.instanceMatrix.needsUpdate = true;
    }

    // 3. Update Sandstorm Simulation
    if (this.sandMesh.visible) {
      const dummy = new THREE.Object3D();
      for (let i = 0; i < this.sandCount; i++) {
        const p = this.sandParticles[i];
        p.x += p.speedX * delta;
        p.z += p.speedZ * delta;

        if (p.x > 65) {
          p.x = -65;
          p.z = (Math.random() - 0.5) * 130;
          p.y = Math.random() * 25 + 0.5;
        }

        dummy.position.set(p.x, p.y, p.z);
        dummy.updateMatrix();
        this.sandMesh.setMatrixAt(i, dummy.matrix);
      }
      this.sandMesh.instanceMatrix.needsUpdate = true;
    }
  }
}
