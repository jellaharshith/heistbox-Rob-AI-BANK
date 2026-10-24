/**
 * HeistBox 3D Scene - Environment Effects, Weather & Time of Day
 * - Weather Modes: Clear Night, Rain, Fog, Sandstorm
 * - Animated Day/Night Cycle (setTimeOfDay)
 * - Camera Screen Shake
 * - 3D BUSTED Stamp overlay
 */

import * as THREE from './three.module.js';

export class EffectsManager {
  constructor(scene, renderer, camera) {
    this.scene = scene;
    this.renderer = renderer;
    this.camera = camera;

    this.weatherMode = 'Clear Night';
    this.timeOfDay = 0.0; // 0.0 = midnight, 0.25 = sunrise, 0.5 = noon, 0.75 = sunset
    this.shakeIntensity = 0;

    this.initLights();
    this.initStars();
    this.initRain();
    this.initSandstorm();
    this.initBustedStamp();

    this.setWeather('Clear Night');
    this.setTimeOfDay(0.0);
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
