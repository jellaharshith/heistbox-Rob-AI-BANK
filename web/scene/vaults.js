/**
 * HeistBox 3D Scene - Vault Logic & Juiced Verdict Visuals
 * - Routing laser conduits from Teller to all 3 vaults
 * - LEFT Vault: Slot-machine SAFE% reel + parabolic coin shower to Van
 * - MIDDLE Vault: Drop-gate lockdown + red alarm strobes + ice freeze
 * - RIGHT Vault: PAIR surgical guillotine slam + laser shredder + rooftop golden Face ID slot
 */

import * as THREE from './three.module.js';
import * as audio from './audio.js';

export class VaultManager {
  constructor(scene, worldManager, armoredVan) {
    this.scene = scene;
    this.worldManager = worldManager;
    this.van = armoredVan;
    this.vaults = worldManager.vaults;

    // Routing packet conduits
    this.routingPackets = [];
    this.coins = [];
    this.shredderSparks = [];
    this.honestCoin = null;

    // States
    this.leftOpen = false;
    this.middleLocked = false;
    this.rightSlammed = false;

    // Coins instanced mesh for high performance
    this.initCoinSystem();
    this.initSparkSystem();
  }

  initCoinSystem() {
    this.maxCoins = 120;
    const coinGeo = new THREE.CylinderGeometry(0.3, 0.3, 0.08, 10);
    const coinMat = new THREE.MeshStandardMaterial({
      color: 0xFFC93C,
      metalness: 0.85,
      roughness: 0.25,
      emissive: 0x553C00,
      emissiveIntensity: 0.3,
    });

    this.coinMesh = new THREE.InstancedMesh(coinGeo, coinMat, this.maxCoins);
    this.coinMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.coinMesh.count = 0;
    this.coinMesh.castShadow = true;
    this.scene.add(this.coinMesh);

    this.activeCoinParticles = [];
  }

  initSparkSystem() {
    this.maxSparks = 80;
    const sparkGeo = new THREE.BoxGeometry(0.12, 0.12, 0.12);
    const sparkMat = new THREE.MeshBasicMaterial({ color: 0xEF4444 });
    this.sparkMesh = new THREE.InstancedMesh(sparkGeo, sparkMat, this.maxSparks);
    this.sparkMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.sparkMesh.count = 0;
    this.scene.add(this.sparkMesh);

    this.activeSparks = [];
  }

  /** Step 2: Fire glowing routing laser packets from Counter to 3 Vaults simultaneously */
  triggerRoutingLaser() {
    const start = new THREE.Vector3(0, 2.2, 0); // Teller Counter
    const destinations = [
      new THREE.Vector3(-18, 2.2, -26), // Left
      new THREE.Vector3(0, 2.2, -26),   // Middle
      new THREE.Vector3(18, 2.2, -26),  // Right
    ];

    destinations.forEach((dest, idx) => {
      const packetGeo = new THREE.SphereGeometry(0.35, 8, 8);
      const packetMat = new THREE.MeshBasicMaterial({
        color: idx === 0 ? 0xFACC15 : idx === 1 ? 0x38BDF8 : 0x10B981,
      });
      const mesh = new THREE.Mesh(packetGeo, packetMat);
      mesh.position.copy(start);
      this.scene.add(mesh);

      this.routingPackets.push({
        mesh,
        start: start.clone(),
        dest: dest.clone(),
        progress: 0,
        speed: 1.8 + idx * 0.1,
      });
    });
  }

  /** Step 3: LEFT Vault "LLM Judge" Naive Robbery */
  triggerLeftRobbery(onComplete = null) {
    const left = this.vaults.left;
    if (!left) return;

    // 1. Slot-machine roll simulation on digital marquee
    let safePct = 12;
    const targetPct = 99;
    const rollInterval = setInterval(() => {
      safePct = Math.min(targetPct, safePct + Math.floor(Math.random() * 12 + 6));
      audio.playReelTick(safePct / 20);

      const ctx = left.ctx;
      ctx.fillStyle = '#0B0F1E';
      ctx.fillRect(0, 0, 256, 80);
      ctx.fillStyle = safePct >= 99 ? '#10B981' : '#FACC15';
      ctx.font = 'bold 36px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`SAFE: ${safePct}%`, 128, 52);
      left.texture.needsUpdate = true;

      if (safePct >= targetPct) {
        clearInterval(rollInterval);
        audio.playReelWin();

        // 2. Door pops open
        this.leftOpen = true;

        // 3. Open van doors and spray gold coin explosion to getaway van
        this.van.openDoors();
        this.sprayCoinsToVan(() => {
          if (onComplete) onComplete();
        });
      }
    }, 110);
  }

  /** Launch a parabolic stream of gold coins from Left Vault to Armored Van */
  sprayCoinsToVan(onFinish = null) {
    audio.playCoinShower(24);

    const vaultPos = new THREE.Vector3(-18, 6.0, -26);
    const vanCargoPos = this.van.mesh.position.clone().add(new THREE.Vector3(0, 1.6, -3.4));

    for (let i = 0; i < 70; i++) {
      const delay = i * 0.025;
      this.activeCoinParticles.push({
        start: vaultPos.clone(),
        target: vanCargoPos.clone().add(new THREE.Vector3((Math.random() - 0.5) * 1.2, (Math.random() - 0.5) * 0.8, (Math.random() - 0.5) * 0.8)),
        arcHeight: 12 + Math.random() * 4,
        progress: -delay,
        speed: 1.1 + Math.random() * 0.3,
        rotSpeed: Math.random() * 15,
        matrix: new THREE.Matrix4(),
      });
    }

    setTimeout(() => {
      if (onFinish) onFinish();
    }, 2400);
  }

  /** Step 4: MIDDLE Vault "Kill-Switch" Panic Lockdown */
  triggerMiddleLockdown(onComplete = null) {
    this.middleLocked = true;
    audio.playLockdownAlarm();

    // Drop steel portcullis security gate
    const mid = this.vaults.middle;
    if (mid && mid.dropGate) {
      mid.dropGateTargetY = 6.0; // Drops from y=15.5 to y=6.0
    }

    // Spawn crystalline cyan ice encasement around honest refund
    this.spawnIceEncasement();

    setTimeout(() => {
      if (onComplete) onComplete();
    }, 1200);
  }

  spawnIceEncasement() {
    audio.playFreezeSound();

    if (this.iceMesh) {
      this.scene.remove(this.iceMesh);
    }

    const iceGroup = new THREE.Group();
    iceGroup.position.set(0, 2.2, 5.0); // At counter where honest transaction was

    const iceMat = new THREE.MeshStandardMaterial({
      color: 0x38BDF8,
      roughness: 0.1,
      metalness: 0.2,
      transparent: true,
      opacity: 0.85,
    });

    // Chunky ice crystal block
    for (let i = 0; i < 5; i++) {
      const geo = new THREE.ConeGeometry(0.6 + i * 0.15, 1.8 + i * 0.3, 5);
      const m = new THREE.Mesh(geo, iceMat);
      m.position.set((Math.random() - 0.5) * 0.8, 0.8 + i * 0.2, (Math.random() - 0.5) * 0.8);
      m.rotation.set(Math.random() * 0.4, Math.random() * Math.PI, Math.random() * 0.4);
      iceGroup.add(m);
    }

    // Floating FROZEN tag
    const canvas = document.createElement('canvas');
    canvas.width = 192;
    canvas.height = 48;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = 'rgba(2, 132, 199, 0.85)';
    ctx.fillRect(0, 0, 192, 48);
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 24px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('🧊 $25 FROZEN', 96, 24);

    const tex = new THREE.CanvasTexture(canvas);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex }));
    sprite.scale.set(2.2, 0.55, 1);
    sprite.position.set(0, 2.8, 0);
    iceGroup.add(sprite);

    this.iceMesh = iceGroup;
    this.scene.add(iceGroup);
  }

  /** Step 5: RIGHT Vault "PAIR Gate" Surgical Defusal */
  triggerRightPAIRDefusal(cameraShakeFn, onComplete = null) {
    this.rightSlammed = true;

    // 1. Mechanical guillotine door slam
    audio.playDoorSlam();
    if (cameraShakeFn) cameraShakeFn(0.6);

    // 2. Route unauthorized $4,975 rows into Shredder Plant
    this.triggerShredderPlant();

    // 3. Route honest $25 up to rooftop iPhone Enclave Stand
    this.routeHonestRefundToRoof();

    setTimeout(() => {
      if (onComplete) onComplete();
    }, 2200);
  }

  triggerShredderPlant() {
    audio.playLaserShredder();

    // Spawn sparks in the Shredder Plant hopper
    const shredderPos = new THREE.Vector3(32, 3.5, -20);

    for (let i = 0; i < 60; i++) {
      this.activeSparks.push({
        pos: shredderPos.clone().add(new THREE.Vector3((Math.random() - 0.5) * 2, 0, (Math.random() - 0.5) * 1.5)),
        vel: new THREE.Vector3((Math.random() - 0.5) * 8, 4 + Math.random() * 8, (Math.random() - 0.5) * 8),
        life: 0.6 + Math.random() * 0.4,
        maxLife: 1.0,
      });
    }
  }

  routeHonestRefundToRoof() {
    // Glowing golden $25 coin travels along pneumatic curve up to rooftop stand
    const start = new THREE.Vector3(18, 6.0, -26); // Right PAIR vault
    const apex = new THREE.Vector3(10, 15.0, -16);
    const roof = new THREE.Vector3(0, 10.2, -5.0); // iPhone stand tray

    const coinGeo = new THREE.CylinderGeometry(0.5, 0.5, 0.12, 16);
    const coinMat = new THREE.MeshStandardMaterial({
      color: 0x10B981,
      emissive: 0x059669,
      emissiveIntensity: 0.6,
      metalness: 0.8,
    });
    const coin = new THREE.Mesh(coinGeo, coinMat);
    coin.rotation.x = Math.PI / 2;
    coin.position.copy(start);
    this.scene.add(coin);

    this.honestCoin = {
      mesh: coin,
      p0: start,
      p1: apex,
      p2: roof,
      progress: 0,
      onArrival: () => {
        audio.playGoldenChime();
        this.spawnFaceIDAuthBadge();
      },
    };
  }

  spawnFaceIDAuthBadge() {
    const badgeGeo = new THREE.RingGeometry(1.6, 1.9, 32);
    const badgeMat = new THREE.MeshBasicMaterial({
      color: 0x10B981,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.9,
    });
    const badge = new THREE.Mesh(badgeGeo, badgeMat);
    badge.rotation.x = Math.PI / 2;
    badge.position.set(0, 18.0, -6);
    this.scene.add(badge);

    // Pop scale animation
    badge.scale.set(0.1, 0.1, 0.1);
    const t0 = performance.now();
    const anim = () => {
      const elapsed = (performance.now() - t0) / 1000;
      if (elapsed < 1.5) {
        const s = Math.min(1.2, elapsed * 2.5);
        badge.scale.set(s, s, s);
        badge.material.opacity = Math.max(0, 1.0 - elapsed / 1.5);
        requestAnimationFrame(anim);
      } else {
        this.scene.remove(badge);
      }
    };
    anim();
  }

  reset() {
    this.leftOpen = false;
    this.middleLocked = false;
    this.rightSlammed = false;

    // Reset Left Vault door and display
    const left = this.vaults.left;
    if (left) {
      left.pivot.rotation.y = 0;
      const ctx = left.ctx;
      ctx.fillStyle = '#0B0F1E';
      ctx.fillRect(0, 0, 256, 80);
      ctx.fillStyle = '#FACC15';
      ctx.font = 'bold 36px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('SAFE: --%', 128, 52);
      left.texture.needsUpdate = true;
    }

    // Reset Middle Vault gate
    const mid = this.vaults.middle;
    if (mid && mid.dropGate) {
      mid.dropGate.position.y = 15.5;
      mid.dropGateTargetY = 15.5;
    }

    // Reset Right Vault
    const right = this.vaults.right;
    if (right) {
      right.upperDoor.position.y = 8.2;
      right.lowerDoor.position.y = 3.8;
    }

    // Clean particles & ice
    this.coinMesh.count = 0;
    this.activeCoinParticles = [];
    this.sparkMesh.count = 0;
    this.activeSparks = [];

    if (this.iceMesh) {
      this.scene.remove(this.iceMesh);
      this.iceMesh = null;
    }

    if (this.honestCoin) {
      this.scene.remove(this.honestCoin.mesh);
      this.honestCoin = null;
    }

    this.van.closeDoors();
  }

  update(delta, time) {
    // 1. Update Left Vault Door Swing
    const left = this.vaults.left;
    if (left) {
      const targetAngle = this.leftOpen ? Math.PI / 1.8 : 0;
      left.pivot.rotation.y = THREE.MathUtils.lerp(left.pivot.rotation.y, targetAngle, delta * 4);
    }

    // 2. Update Middle Vault Drop-Gate & Siren
    const mid = this.vaults.middle;
    if (mid) {
      if (mid.dropGateTargetY !== undefined) {
        mid.dropGate.position.y = THREE.MathUtils.lerp(mid.dropGate.position.y, mid.dropGateTargetY, delta * 8);
      }
      if (this.middleLocked && mid.siren) {
        mid.siren.rotation.y += delta * 12;
        mid.siren.material.emissiveIntensity = 0.5 + Math.sin(time * 16) * 0.5;
      }
    }

    // 3. Update Right PAIR Door Slam
    const right = this.vaults.right;
    if (right) {
      const targetUpperY = this.rightSlammed ? 6.2 : 8.2;
      const targetLowerY = this.rightSlammed ? 5.8 : 3.8;
      right.upperDoor.position.y = THREE.MathUtils.lerp(right.upperDoor.position.y, targetUpperY, delta * 14);
      right.lowerDoor.position.y = THREE.MathUtils.lerp(right.lowerDoor.position.y, targetLowerY, delta * 14);
    }

    // 4. Update Routing Packets
    for (let i = this.routingPackets.length - 1; i >= 0; i--) {
      const p = this.routingPackets[i];
      p.progress += delta * p.speed;
      if (p.progress >= 1.0) {
        this.scene.remove(p.mesh);
        this.routingPackets.splice(i, 1);
      } else {
        p.mesh.position.lerpVectors(p.start, p.dest, p.progress);
        p.mesh.position.y = 2.2 + Math.sin(p.progress * Math.PI) * 1.5;
      }
    }

    // 5. Update Gold Coins Explosion
    let liveCoinCount = 0;
    const dummy = new THREE.Object3D();

    for (let i = this.activeCoinParticles.length - 1; i >= 0; i--) {
      const c = this.activeCoinParticles[i];
      c.progress += delta * c.speed;

      if (c.progress >= 1.0) {
        this.activeCoinParticles.splice(i, 1);
      } else if (c.progress > 0) {
        // Parabolic arc interpolation
        const currentPos = new THREE.Vector3().lerpVectors(c.start, c.target, c.progress);
        currentPos.y += Math.sin(c.progress * Math.PI) * c.arcHeight;

        dummy.position.copy(currentPos);
        dummy.rotation.x += delta * c.rotSpeed;
        dummy.rotation.z += delta * c.rotSpeed * 0.8;
        dummy.updateMatrix();

        this.coinMesh.setMatrixAt(liveCoinCount, dummy.matrix);
        liveCoinCount++;
      }
    }

    this.coinMesh.count = liveCoinCount;
    if (liveCoinCount > 0) {
      this.coinMesh.instanceMatrix.needsUpdate = true;
    }

    // 6. Update Shredder Sparks
    let liveSparkCount = 0;
    const sparkDummy = new THREE.Object3D();

    for (let i = this.activeSparks.length - 1; i >= 0; i--) {
      const s = this.activeSparks[i];
      s.life -= delta;

      if (s.life <= 0) {
        this.activeSparks.splice(i, 1);
      } else {
        s.vel.y -= 18 * delta; // Gravity
        s.pos.addScaledVector(s.vel, delta);

        sparkDummy.position.copy(s.pos);
        const scale = s.life / s.maxLife;
        sparkDummy.scale.set(scale, scale, scale);
        sparkDummy.updateMatrix();

        this.sparkMesh.setMatrixAt(liveSparkCount, sparkDummy.matrix);
        liveSparkCount++;
      }
    }

    this.sparkMesh.count = liveSparkCount;
    if (liveSparkCount > 0) {
      this.sparkMesh.instanceMatrix.needsUpdate = true;
    }

    // 7. Update Honest $25 Conduit Coin
    if (this.honestCoin) {
      const hc = this.honestCoin;
      hc.progress += delta * 0.85;

      if (hc.progress >= 1.0) {
        hc.mesh.position.copy(hc.p2);
        hc.onArrival();
        this.honestCoin = null;
      } else {
        // Quadratic bezier curve from PAIR vault to rooftop iPhone stand
        const t = hc.progress;
        const mt = 1 - t;
        hc.mesh.position.x = mt * mt * hc.p0.x + 2 * mt * t * hc.p1.x + t * t * hc.p2.x;
        hc.mesh.position.y = mt * mt * hc.p0.y + 2 * mt * t * hc.p1.y + t * t * hc.p2.y;
        hc.mesh.position.z = mt * mt * hc.p0.z + 2 * mt * t * hc.p1.z + t * t * hc.p2.z;
        hc.mesh.rotation.y += delta * 12;
      }
    }
  }
}
