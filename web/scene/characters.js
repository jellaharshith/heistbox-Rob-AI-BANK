/**
 * HeistBox 3D Scene - Low-Poly Clay Agents & Characters
 * Exactly matches HeistBox API Contract v1.0.0:
 * - Tina: Teller Tina (Teller Counter)
 * - Marcus: Manager Marcus (Manager Office)
 * - Ada: Auditor Ada (Vault Hall)
 * - Gus: Guard Gus (Security Guard, raises Wanted Stars)
 * - Izzy: Intern Izzy (Server Room, bribable)
 * - Thief: Attacker ("Grandma Trickster")
 *
 * Features:
 * - Procedural bobbing walk, idle breathing, and talking animations
 * - Speech/emote bubbles (💬, ❓, 🚨, 💰, 🧊, ⚡) with text support
 * - Overhead name tags
 * - Queueing & Give-Way Logic (teller queue slots, doorway mutex, pedestrian avoidance)
 */

import * as THREE from './three.module.js';

export const ROLE_COLORS = {
  thief: { body: 0x1E293B, accent: 0xFACC15, skin: 0xF5D0C5, hat: 0x0F172A },
  teller: { body: 0x0D9488, accent: 0x14B8A6, skin: 0xE2B8A6, hat: null },
  guard: { body: 0x1E3A8A, accent: 0xFACC15, skin: 0xE8C4B8, hat: 0x1E3A8A },
  manager: { body: 0x6B21A8, accent: 0xFACC15, skin: 0xF5D0C5, hat: null },
  auditor: { body: 0x0369A1, accent: 0x38BDF8, skin: 0xE2B8A6, hat: null },
  intern: { body: 0x475569, accent: 0x94A3B8, skin: 0xF3C9BC, hat: null },
  police: { body: 0x2563EB, accent: 0xEF4444, skin: 0xE2B8A6, hat: 0x1D4ED8 },
  pedestrian: { body: 0xD97706, accent: 0xCBD5E1, skin: 0xF3C9BC, hat: null },
};

export class Character {
  constructor(options = {}) {
    this.id = options.id || `agent_${Math.random().toString(36).substr(2, 6)}`;
    this.name = options.name || 'Citizen';
    this.role = options.role || 'pedestrian';
    this.position = options.position ? options.position.clone() : new THREE.Vector3();
    this.target = null;
    this.waypoints = [];
    this.speed = options.speed || 4.2;
    this.state = 'idle'; // 'idle', 'walking', 'talking', 'queued', 'fleeing', 'busted'

    // Queue & Give-Way parameters
    this.queueSlot = null;
    this.waitingFor = null;
    this.collisionRadius = 0.8;

    this.mesh = this.buildMesh();
    this.mesh.position.copy(this.position);
    this.mesh.userData = {
      isEntity: true,
      id: this.id,
      name: this.name,
      type: 'character',
      role: this.role,
      character: this,
    };

    // Bubble Emote / Speech billboard
    this.bubbleMesh = this.createSpeechBubble();
    this.mesh.add(this.bubbleMesh);
    this.bubbleMesh.visible = false;
    this.bubbleTimeout = null;

    // Overhead Name tag
    this.nameTagMesh = this.createNameTag();
    this.mesh.add(this.nameTagMesh);

    // Animation internal states
    this.walkCycle = Math.random() * Math.PI * 2;
    this.idleCycle = Math.random() * Math.PI * 2;
  }

  buildMesh() {
    const group = new THREE.Group();
    const colors = ROLE_COLORS[this.role] || ROLE_COLORS.pedestrian;

    const bodyMat = new THREE.MeshStandardMaterial({ color: colors.body, roughness: 0.7, metalness: 0.1 });
    const skinMat = new THREE.MeshStandardMaterial({ color: colors.skin, roughness: 0.6, metalness: 0.05 });
    const darkMat = new THREE.MeshStandardMaterial({ color: 0x0F172A, roughness: 0.8, metalness: 0.2 });
    const accentMat = new THREE.MeshStandardMaterial({ color: colors.accent, roughness: 0.5, metalness: 0.3 });

    // Torso / Body (Chunky clay block)
    const torsoGeo = new THREE.BoxGeometry(0.75, 0.95, 0.45);
    this.torso = new THREE.Mesh(torsoGeo, bodyMat);
    this.torso.position.y = 1.05;
    this.torso.castShadow = true;
    group.add(this.torso);

    // Head
    const headGeo = new THREE.BoxGeometry(0.55, 0.55, 0.5);
    this.head = new THREE.Mesh(headGeo, skinMat);
    this.head.position.y = 1.85;
    this.head.castShadow = true;
    group.add(this.head);

    // Role-specific Accessories
    if (this.role === 'thief') {
      // Dark Hoodie & Shades
      const hoodie = new THREE.Mesh(new THREE.BoxGeometry(0.65, 0.4, 0.6), darkMat);
      hoodie.position.set(0, 2.05, -0.05);
      group.add(hoodie);

      const shades = new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.14, 0.08), darkMat);
      shades.position.set(0, 1.88, 0.27);
      group.add(shades);
    } else if (this.role === 'guard' || this.role === 'police') {
      // Peaked Cap & Golden Badge
      const capMat = new THREE.MeshStandardMaterial({ color: colors.hat, roughness: 0.5 });
      const cap = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.2, 0.62), capMat);
      cap.position.set(0, 2.15, 0);
      group.add(cap);

      const visor = new THREE.Mesh(new THREE.BoxGeometry(0.56, 0.06, 0.3), darkMat);
      visor.position.set(0, 2.08, 0.36);
      group.add(visor);

      const badge = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.2, 0.04), accentMat);
      badge.position.set(0.18, 1.25, 0.24);
      group.add(badge);
    } else if (this.role === 'manager') {
      // Sleek slicked hair & Gold tie
      const hair = new THREE.Mesh(new THREE.BoxGeometry(0.58, 0.18, 0.54), darkMat);
      hair.position.set(0, 2.15, 0);
      group.add(hair);

      const tie = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.5, 0.04), accentMat);
      tie.position.set(0, 1.15, 0.24);
      group.add(tie);
    } else if (this.role === 'auditor') {
      // Wire-frame glasses & clipboard
      const glasses = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.12, 0.06), accentMat);
      glasses.position.set(0, 1.88, 0.26);
      group.add(glasses);

      const board = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.5, 0.06), new THREE.MeshStandardMaterial({ color: 0x78350F }));
      board.position.set(0.55, 1.05, 0.25);
      board.rotation.y = -Math.PI / 6;
      group.add(board);
    } else if (this.role === 'intern') {
      // Lanyard & messy hair
      const hair = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.26, 0.56), darkMat);
      hair.position.set(0, 2.14, 0);
      group.add(hair);

      const lanyard = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.3, 0.04), accentMat);
      lanyard.position.set(0, 1.1, 0.24);
      group.add(lanyard);
    } else {
      // Neat hair
      const hair = new THREE.Mesh(
        new THREE.BoxGeometry(0.58, 0.22, 0.54),
        new THREE.MeshStandardMaterial({ color: 0x451A03, roughness: 0.8 })
      );
      hair.position.set(0, 2.14, 0);
      group.add(hair);
    }

    // Arms
    const armGeo = new THREE.BoxGeometry(0.22, 0.75, 0.22);
    this.leftArm = new THREE.Mesh(armGeo, bodyMat);
    this.leftArm.position.set(-0.52, 1.05, 0);
    this.leftArm.castShadow = true;
    group.add(this.leftArm);

    this.rightArm = new THREE.Mesh(armGeo, bodyMat);
    this.rightArm.position.set(0.52, 1.05, 0);
    this.rightArm.castShadow = true;
    group.add(this.rightArm);

    // Legs
    const legGeo = new THREE.BoxGeometry(0.26, 0.75, 0.26);
    this.leftLeg = new THREE.Mesh(legGeo, darkMat);
    this.leftLeg.position.set(-0.2, 0.38, 0);
    this.leftLeg.castShadow = true;
    group.add(this.leftLeg);

    this.rightLeg = new THREE.Mesh(legGeo, darkMat);
    this.rightLeg.position.set(0.2, 0.38, 0);
    this.rightLeg.castShadow = true;
    group.add(this.rightLeg);

    return group;
  }

  createNameTag() {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 54;
    const ctx = canvas.getContext('2d');

    ctx.fillStyle = 'rgba(11, 15, 30, 0.88)';
    ctx.fillRect(0, 0, 256, 54);
    ctx.strokeStyle = '#FFC93C';
    ctx.lineWidth = 3;
    ctx.strokeRect(2, 2, 252, 50);

    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 22px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(this.name, 128, 27);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, depthTest: false });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.scale.set(1.8, 0.42, 1);
    sprite.position.set(0, 2.65, 0);
    return sprite;
  }

  createSpeechBubble() {
    this.bubbleCanvas = document.createElement('canvas');
    this.bubbleCanvas.width = 256;
    this.bubbleCanvas.height = 128;
    this.bubbleCtx = this.bubbleCanvas.getContext('2d');

    this.bubbleTexture = new THREE.CanvasTexture(this.bubbleCanvas);
    const mat = new THREE.SpriteMaterial({ map: this.bubbleTexture, depthTest: false });
    const sprite = new THREE.Sprite(mat);
    sprite.scale.set(2.4, 1.2, 1);
    sprite.position.set(0, 3.4, 0);
    return sprite;
  }

  /** Display speech or emote bubble with text/icon */
  showEmote(textOrEmoji, durationMs = 3500) {
    if (this.bubbleTimeout) clearTimeout(this.bubbleTimeout);

    const ctx = this.bubbleCtx;
    ctx.clearRect(0, 0, 256, 128);

    // Rounded Speech bubble background
    ctx.fillStyle = '#FFFFFF';
    ctx.beginPath();
    ctx.roundRect(10, 10, 236, 85, 20);
    ctx.fill();

    // Bubble pointer beak
    ctx.beginPath();
    ctx.moveTo(116, 95);
    ctx.lineTo(128, 118);
    ctx.lineTo(140, 95);
    ctx.fill();

    // Border
    ctx.strokeStyle = '#0B0F1E';
    ctx.lineWidth = 3;
    ctx.stroke();

    ctx.fillStyle = '#0B0F1E';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    if (textOrEmoji.length <= 4) {
      // Big Emoji
      ctx.font = '54px sans-serif';
      ctx.fillText(textOrEmoji, 128, 52);
    } else {
      // Text Line
      ctx.font = 'bold 18px sans-serif';
      const maxW = 210;
      let line = textOrEmoji;
      if (ctx.measureText(line).width > maxW) {
        line = line.substring(0, 22) + '...';
      }
      ctx.fillText(line, 128, 52);
    }

    this.bubbleTexture.needsUpdate = true;
    this.bubbleMesh.visible = true;

    this.bubbleTimeout = setTimeout(() => {
      this.bubbleMesh.visible = false;
    }, durationMs);
  }

  setDestination(x, z, onArrival = null) {
    this.target = new THREE.Vector3(x, 0, z);
    this.onArrival = onArrival;
    this.state = 'walking';
  }

  setPath(waypoints, onComplete = null) {
    this.waypoints = waypoints.map((p) => new THREE.Vector3(p[0], 0, p[1]));
    this.onPathComplete = onComplete;
    if (this.waypoints.length > 0) {
      this.target = this.waypoints.shift();
      this.state = 'walking';
    }
  }

  update(delta, time, worldManager, allCharacters) {
    // 1. Give-Way & Collision avoidance
    let effectiveSpeed = this.speed;

    if (this.state === 'walking' && this.target) {
      const toTarget = this.target.clone().sub(this.position);
      const dist = toTarget.length();

      if (dist < 0.15) {
        this.position.copy(this.target);
        if (this.waypoints.length > 0) {
          this.target = this.waypoints.shift();
        } else {
          this.target = null;
          this.state = 'idle';
          if (this.onArrival) {
            const cb = this.onArrival;
            this.onArrival = null;
            cb();
          }
          if (this.onPathComplete) {
            const cb = this.onPathComplete;
            this.onPathComplete = null;
            cb();
          }
        }
      } else {
        // Check for give-way: another character standing in front
        let blocked = false;
        const forward = toTarget.clone().normalize();

        for (const other of allCharacters) {
          if (other === this) continue;
          const toOther = other.position.clone().sub(this.position);
          const otherDist = toOther.length();

          if (otherDist < 1.3) {
            const dot = forward.dot(toOther.normalize());
            if (dot > 0.6) {
              // Yield / Wait in queue
              blocked = true;
              break;
            }
          }
        }

        if (blocked) {
          effectiveSpeed = 0; // Wait patiently without clipping!
        } else {
          toTarget.normalize();
          this.position.addScaledVector(toTarget, effectiveSpeed * delta);

          const targetAngle = Math.atan2(toTarget.x, toTarget.z);
          this.mesh.rotation.y = THREE.MathUtils.lerp(this.mesh.rotation.y, targetAngle, delta * 12);
        }
      }
    }

    this.mesh.position.copy(this.position);

    // 2. Procedural Animation Cycles
    if (this.state === 'walking' && effectiveSpeed > 0.1) {
      this.walkCycle += delta * 10;
      const legAngle = Math.sin(this.walkCycle) * 0.6;
      const armAngle = -Math.sin(this.walkCycle) * 0.6;

      this.leftLeg.rotation.x = legAngle;
      this.rightLeg.rotation.x = -legAngle;
      this.leftArm.rotation.x = armAngle;
      this.rightArm.rotation.x = -armAngle;

      this.torso.position.y = 1.05 + Math.abs(Math.sin(this.walkCycle * 2)) * 0.08;
      this.head.position.y = 1.85 + Math.abs(Math.sin(this.walkCycle * 2)) * 0.08;
    } else {
      this.idleCycle += delta * 2.5;

      this.leftLeg.rotation.x = THREE.MathUtils.lerp(this.leftLeg.rotation.x, 0, delta * 8);
      this.rightLeg.rotation.x = THREE.MathUtils.lerp(this.rightLeg.rotation.x, 0, delta * 8);
      this.leftArm.rotation.x = THREE.MathUtils.lerp(this.leftArm.rotation.x, 0, delta * 8);
      this.rightArm.rotation.x = THREE.MathUtils.lerp(this.rightArm.rotation.x, 0, delta * 8);

      this.torso.position.y = 1.05 + Math.sin(this.idleCycle) * 0.03;
      this.head.position.y = 1.85 + Math.sin(this.idleCycle) * 0.03;

      if (this.state === 'talking') {
        this.leftArm.rotation.x = Math.sin(this.idleCycle * 3) * 0.35;
        this.rightArm.rotation.x = -Math.cos(this.idleCycle * 3) * 0.35;
        this.head.rotation.y = Math.sin(this.idleCycle * 2) * 0.15;
      }
    }

    if (this.bubbleMesh.visible) {
      this.bubbleMesh.position.y = 3.4 + Math.sin(time * 4) * 0.08;
    }
  }
}

export class CharacterManager {
  constructor(scene, worldManager) {
    this.scene = scene;
    this.worldManager = worldManager;
    this.characters = [];
    this.agentMap = {};

    this.spawnContractAgents();
  }

  spawnContractAgents() {
    // 1. Tina: "Teller Tina" (Teller Counter)
    this.tina = new Character({
      id: 'tina',
      name: 'Teller Tina',
      role: 'teller',
      position: new THREE.Vector3(0, 0, -0.6),
    });
    this.addCharacter(this.tina);

    // 2. Marcus: "Manager Marcus" (Manager Office)
    this.marcus = new Character({
      id: 'marcus',
      name: 'Manager Marcus',
      role: 'manager',
      position: new THREE.Vector3(-13, 4.2, -10),
    });
    this.addCharacter(this.marcus);

    // 3. Gus: "Guard Gus" (Lobby Security, raises Wanted Stars)
    this.gus = new Character({
      id: 'gus',
      name: 'Guard Gus',
      role: 'guard',
      position: new THREE.Vector3(-10, 0, 16),
      speed: 3.2,
    });
    this.addCharacter(this.gus);
    this.setupPatrol(this.gus, [
      [-10, 16], [-10, 2], [10, 2], [10, 16]
    ]);

    // 4. Ada: "Auditor Ada" (Vault Corridor)
    this.ada = new Character({
      id: 'ada',
      name: 'Auditor Ada',
      role: 'auditor',
      position: new THREE.Vector3(-6, 0, -22),
      speed: 3.0,
    });
    this.addCharacter(this.ada);
    this.setupPatrol(this.ada, [
      [-6, -22], [12, -22], [12, -18], [-6, -18]
    ]);

    // 5. Izzy: "Intern Izzy" (Server Room)
    this.izzy = new Character({
      id: 'izzy',
      name: 'Intern Izzy',
      role: 'intern',
      position: new THREE.Vector3(22, 0, -10),
      speed: 2.8,
    });
    this.addCharacter(this.izzy);
    this.setupPatrol(this.izzy, [
      [22, -10], [18, -4], [26, -4], [22, -10]
    ]);

    // 6. The Thief ("Grandma Trickster" / Attacker)
    this.thief = new Character({
      id: 'thief',
      name: 'Grandma Trickster',
      role: 'thief',
      position: new THREE.Vector3(0, 0, 36), // Plaza entrance
      speed: 4.8,
    });
    this.addCharacter(this.thief);

    // 7. Ambient Las Vegas Pedestrians
    const ped1 = new Character({
      id: 'ped_1',
      name: 'High Roller Leo',
      role: 'pedestrian',
      position: new THREE.Vector3(-22, 0, 28),
      speed: 2.8,
    });
    this.addCharacter(ped1);
    this.setupPatrol(ped1, [
      [-22, 28], [-28, 42], [-14, 42], [-22, 28]
    ]);
  }

  addCharacter(char) {
    this.characters.push(char);
    this.agentMap[char.id] = char;
    this.scene.add(char.mesh);
    this.worldManager.interactiveEntities.push(char.mesh);
  }

  getAgent(id) {
    return this.agentMap[id] || null;
  }

  setupPatrol(char, waypoints) {
    let index = 0;
    const nextLeg = () => {
      index = (index + 1) % waypoints.length;
      char.setDestination(waypoints[index][0], waypoints[index][1], () => {
        setTimeout(nextLeg, 1200 + Math.random() * 1000);
      });
    };
    nextLeg();
  }

  update(delta, time) {
    this.characters.forEach((c) => c.update(delta, time, this.worldManager, this.characters));
  }
}
