/**
 * HeistBox 3D Scene - World Architecture & Procedural Campus Builder
 * Builds a low-poly isometric Vegas-style bank campus entirely in code.
 * Clean toy-like clay look, soft shadows, accent color #FFC93C, midnight #0B0F1E.
 */

import * as THREE from './three.module.js';
import { createAvatarTexture } from './avatar.js';

export const COLORS = {
  background: 0x0B0F1E,
  accentGold: 0xFFC93C,
  goldDark: 0xD49A16,
  clayNavy: 0x162038,
  clayDeepNavy: 0x0E1626,
  clayDark: 0x1E293B,
  clayLight: 0xE2E8F0,
  clayStone: 0x94A3B8,
  clayWarm: 0xF8FAFC,
  clayGlass: 0x38BDF8,
  redAlert: 0xEF4444,
  greenSafe: 0x10B981,
  roadAsphalt: 0x131A29,
  sidewalk: 0x222E46,
  paverGold: 0x2C281E,
  grassClay: 0x1A2E26,
  policeBlue: 0x2563EB,
};

export class WorldManager {
  constructor(scene) {
    this.scene = scene;
    this.landmarks = {};
    this.interactiveEntities = [];
    this.animatedObjects = [];
    this.tickerMesh = null;
    this.tickerCanvas = null;
    this.tickerCtx = null;
    this.tickerOffset = 0;
    this.blinkingLeds = [];
    this.materials = this.initMaterials();

    this.buildCampus();
  }

  initMaterials() {
    // Clay-style materials with uniform roughness and tactile toy-like quality
    return {
      ground: new THREE.MeshStandardMaterial({
        color: COLORS.clayDeepNavy,
        roughness: 0.85,
        metalness: 0.1,
      }),
      road: new THREE.MeshStandardMaterial({
        color: COLORS.roadAsphalt,
        roughness: 0.9,
        metalness: 0.05,
      }),
      sidewalk: new THREE.MeshStandardMaterial({
        color: COLORS.sidewalk,
        roughness: 0.8,
        metalness: 0.1,
      }),
      plazaPavers: new THREE.MeshStandardMaterial({
        color: COLORS.paverGold,
        roughness: 0.75,
        metalness: 0.15,
      }),
      grass: new THREE.MeshStandardMaterial({
        color: COLORS.grassClay,
        roughness: 0.95,
        metalness: 0.0,
      }),
      bankWalls: new THREE.MeshStandardMaterial({
        color: COLORS.clayNavy,
        roughness: 0.65,
        metalness: 0.15,
      }),
      bankTrim: new THREE.MeshStandardMaterial({
        color: COLORS.accentGold,
        roughness: 0.45,
        metalness: 0.35,
      }),
      whiteStone: new THREE.MeshStandardMaterial({
        color: COLORS.clayLight,
        roughness: 0.6,
        metalness: 0.1,
      }),
      darkMetal: new THREE.MeshStandardMaterial({
        color: 0x242D3D,
        roughness: 0.5,
        metalness: 0.5,
      }),
      goldAccent: new THREE.MeshStandardMaterial({
        color: COLORS.accentGold,
        roughness: 0.35,
        metalness: 0.6,
        emissive: 0x553C00,
        emissiveIntensity: 0.25,
      }),
      glass: new THREE.MeshStandardMaterial({
        color: COLORS.clayGlass,
        roughness: 0.2,
        metalness: 0.3,
        transparent: true,
        opacity: 0.6,
      }),
      hazardStripe: new THREE.MeshStandardMaterial({
        color: 0xFACC15,
        roughness: 0.6,
        metalness: 0.2,
      }),
      hazardBlack: new THREE.MeshStandardMaterial({
        color: 0x111827,
        roughness: 0.6,
        metalness: 0.2,
      }),
      roofStone: new THREE.MeshStandardMaterial({
        color: 0x1B2436,
        roughness: 0.8,
        metalness: 0.1,
      }),
      shredderSteel: new THREE.MeshStandardMaterial({
        color: 0x475569,
        roughness: 0.4,
        metalness: 0.7,
      }),
      serverRack: new THREE.MeshStandardMaterial({
        color: 0x0F172A,
        roughness: 0.5,
        metalness: 0.4,
      }),
      neonRed: new THREE.MeshStandardMaterial({
        color: 0xFF2222,
        emissive: 0xFF1111,
        emissiveIntensity: 0.8,
      }),
      neonGreen: new THREE.MeshStandardMaterial({
        color: 0x10B981,
        emissive: 0x059669,
        emissiveIntensity: 0.8,
      }),
      neonBlue: new THREE.MeshStandardMaterial({
        color: 0x38BDF8,
        emissive: 0x0284C7,
        emissiveIntensity: 0.8,
      }),
    };
  }

  buildCampus() {
    this.buildTerrainAndRoads();
    this.buildMainBankLobby();
    this.buildTellerCounter();
    this.buildManagerOffice();
    this.buildServerRoom();
    this.buildVaultHall();
    this.buildShredderPlant();
    this.buildCasinoJackpotTower();
    this.buildPoliceStation();
    this.buildGetawayGarage();
    this.buildiPhoneEnclaveStand();
    this.buildEnvironmentProps();
  }

  buildTerrainAndRoads() {
    const group = new THREE.Group();
    group.name = "TerrainAndRoads";

    // Campus foundation base
    const baseGeo = new THREE.BoxGeometry(140, 2, 140);
    const baseMesh = new THREE.Mesh(baseGeo, this.materials.ground);
    baseMesh.position.y = -1;
    baseMesh.receiveShadow = true;
    group.add(baseMesh);

    // Perimeter Road (Loop around campus)
    const roadMat = this.materials.road;
    const roadWidth = 14;

    // Outer road ring segments
    const roads = [
      { w: 130, h: 0.1, d: roadWidth, x: 0, z: 52 },   // Front road
      { w: 130, h: 0.1, d: roadWidth, x: 0, z: -52 },  // Back road
      { w: roadWidth, h: 0.1, d: 118, x: -56, z: 0 },  // Left road
      { w: roadWidth, h: 0.1, d: 118, x: 56, z: 0 },   // Right road
    ];

    roads.forEach((r) => {
      const geo = new THREE.BoxGeometry(r.w, r.h, r.d);
      const mesh = new THREE.Mesh(geo, roadMat);
      mesh.position.set(r.x, 0.05, r.z);
      mesh.receiveShadow = true;
      group.add(mesh);
    });

    // Central Bank Plaza (Terracotta/Slate clay tiles)
    const plazaGeo = new THREE.BoxGeometry(94, 0.2, 86);
    const plaza = new THREE.Mesh(plazaGeo, this.materials.sidewalk);
    plaza.position.set(0, 0.1, 0);
    plaza.receiveShadow = true;
    group.add(plaza);

    // Gold inlaid promenade leading from front road to Lobby entrance
    const promGeo = new THREE.BoxGeometry(18, 0.25, 46);
    const promenade = new THREE.Mesh(promGeo, this.materials.plazaPavers);
    promenade.position.set(0, 0.12, 22);
    promenade.receiveShadow = true;
    group.add(promenade);

    // Inlaid gold pathway lines
    const stripeMat = this.materials.bankTrim;
    [-7, 0, 7].forEach((x) => {
      const stripeGeo = new THREE.BoxGeometry(0.6, 0.26, 44);
      const stripe = new THREE.Mesh(stripeGeo, stripeMat);
      stripe.position.set(x, 0.13, 22);
      group.add(stripe);
    });

    // Decorative grass flowerbeds along promenade
    const bedGeo = new THREE.BoxGeometry(10, 0.4, 30);
    [-18, 18].forEach((x) => {
      const bed = new THREE.Mesh(bedGeo, this.materials.grass);
      bed.position.set(x, 0.2, 22);
      bed.receiveShadow = true;
      group.add(bed);

      // Low-poly clay hedges
      const hedgeGeo = new THREE.BoxGeometry(8, 1.2, 28);
      const hedgeMat = new THREE.MeshStandardMaterial({ color: 0x1E3A2F, roughness: 0.9 });
      const hedge = new THREE.Mesh(hedgeGeo, hedgeMat);
      hedge.position.set(x, 0.8, 22);
      hedge.castShadow = true;
      hedge.receiveShadow = true;
      group.add(hedge);
    });

    this.scene.add(group);
  }

  // 1. MAIN BANK LOBBY (Open Cutaway Diorama)
  buildMainBankLobby() {
    const group = new THREE.Group();
    group.name = "MainBankLobby";
    group.position.set(0, 0, -6);

    // Marble Lobby Floor Slab
    const floorGeo = new THREE.BoxGeometry(40, 0.4, 28);
    const floor = new THREE.Mesh(floorGeo, this.materials.whiteStone);
    floor.position.set(0, 0.2, 0);
    floor.receiveShadow = true;
    group.add(floor);

    // Polished Inlaid Border Pattern on floor
    const borderMat = this.materials.bankTrim;
    const borderGeo = new THREE.BoxGeometry(39, 0.42, 27);
    const borderLines = new THREE.Mesh(borderGeo, borderMat);
    borderLines.position.set(0, 0.19, 0);
    group.add(borderLines);

    // Interior floor center inlay
    const innerFloor = new THREE.Mesh(
      new THREE.BoxGeometry(37, 0.44, 25),
      new THREE.MeshStandardMaterial({ color: 0xF1F5F9, roughness: 0.3, metalness: 0.2 })
    );
    innerFloor.position.set(0, 0.21, 0);
    innerFloor.receiveShadow = true;
    group.add(innerFloor);

    // Cutaway Back Wall (Low wall separating lobby from vault corridor)
    // Left back wall segment
    const backWallLeft = new THREE.Mesh(new THREE.BoxGeometry(15, 5.0, 1.2), this.materials.bankWalls);
    backWallLeft.position.set(-11.5, 2.7, -13.4);
    backWallLeft.castShadow = true;
    backWallLeft.receiveShadow = true;
    group.add(backWallLeft);

    // Right back wall segment
    const backWallRight = new THREE.Mesh(new THREE.BoxGeometry(15, 5.0, 1.2), this.materials.bankWalls);
    backWallRight.position.set(11.5, 2.7, -13.4);
    backWallRight.castShadow = true;
    backWallRight.receiveShadow = true;
    group.add(backWallRight);

    // Central Archway Header connecting Lobby to Vault Hall
    const archHeader = new THREE.Mesh(new THREE.BoxGeometry(10, 1.5, 1.4), this.materials.bankTrim);
    archHeader.position.set(0, 5.2, -13.4);
    group.add(archHeader);

    // Left and Right Cutaway Exterior Walls (Low side walls)
    const leftWall = new THREE.Mesh(new THREE.BoxGeometry(1.2, 4.0, 28), this.materials.bankWalls);
    leftWall.position.set(-19.4, 2.2, 0);
    leftWall.castShadow = true;
    group.add(leftWall);

    const rightWall = new THREE.Mesh(new THREE.BoxGeometry(1.2, 4.0, 28), this.materials.bankWalls);
    rightWall.position.set(19.4, 2.2, 0);
    rightWall.castShadow = true;
    group.add(rightWall);

    // Gold Cornice Trim along top of walls
    const trimLeft = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.35, 28.2), this.materials.bankTrim);
    trimLeft.position.set(-19.4, 4.3, 0);
    group.add(trimLeft);

    const trimRight = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.35, 28.2), this.materials.bankTrim);
    trimRight.position.set(19.4, 4.3, 0);
    group.add(trimRight);

    // Front Low Balustrades flanking entrance
    const balustradeMat = this.materials.whiteStone;
    [-13, 13].forEach((bx) => {
      const bal = new THREE.Mesh(new THREE.BoxGeometry(10, 1.6, 1.0), balustradeMat);
      bal.position.set(bx, 1.0, 13.5);
      group.add(bal);

      const balTrim = new THREE.Mesh(new THREE.BoxGeometry(10.2, 0.25, 1.2), this.materials.bankTrim);
      balTrim.position.set(bx, 1.9, 13.5);
      group.add(balTrim);
    });

    // 4 Grand Classical Columns flanking the entrance
    const colGeo = new THREE.CylinderGeometry(0.7, 0.85, 8.0, 8);
    const colPositions = [-14, -6, 6, 14];
    colPositions.forEach((x) => {
      const col = new THREE.Mesh(colGeo, this.materials.whiteStone);
      col.position.set(x, 4.2, 13.5);
      col.castShadow = true;
      group.add(col);

      // Gold capital & base
      const capGeo = new THREE.BoxGeometry(2.0, 0.5, 2.0);
      const cap = new THREE.Mesh(capGeo, this.materials.bankTrim);
      cap.position.set(x, 8.4, 13.5);
      group.add(cap);

      const base = new THREE.Mesh(capGeo, this.materials.bankTrim);
      base.position.set(x, 0.45, 13.5);
      group.add(base);
    });

    // Grand Entrance Stairs
    for (let i = 0; i < 4; i++) {
      const stairGeo = new THREE.BoxGeometry(28 - i * 1.5, 0.35, 2.2);
      const stair = new THREE.Mesh(stairGeo, this.materials.whiteStone);
      stair.position.set(0, 0.17 + i * 0.35, 14.5 + (3 - i) * 1.4);
      stair.receiveShadow = true;
      group.add(stair);
    }

    // Revolving Brass Door in center
    const doorFrameGeo = new THREE.CylinderGeometry(3.6, 3.6, 4.6, 16, 1, true);
    const doorFrame = new THREE.Mesh(doorFrameGeo, this.materials.glass);
    doorFrame.position.set(0, 2.4, 13.2);
    group.add(doorFrame);

    const doorCenterPole = new THREE.Mesh(
      new THREE.CylinderGeometry(0.2, 0.2, 4.6, 8),
      this.materials.bankTrim
    );
    doorCenterPole.position.set(0, 2.4, 13.2);
    group.add(doorCenterPole);

    // Revolving wings
    const revolvingWings = new THREE.Group();
    revolvingWings.position.set(0, 2.4, 13.2);
    for (let i = 0; i < 4; i++) {
      const wingGeo = new THREE.BoxGeometry(3.2, 4.4, 0.15);
      const wing = new THREE.Mesh(wingGeo, this.materials.bankTrim);
      wing.position.x = 1.6;
      const pivot = new THREE.Group();
      pivot.rotation.y = (i * Math.PI) / 2;
      pivot.add(wing);
      revolvingWings.add(pivot);
    }
    group.add(revolvingWings);
    this.animatedObjects.push((delta) => {
      revolvingWings.rotation.y += delta * 0.4;
    });

    // Vegas Marquee Signboard mounted above revolving door
    const signBoard = new THREE.Mesh(
      new THREE.BoxGeometry(16, 1.8, 0.4),
      new THREE.MeshStandardMaterial({ color: 0x070B14, roughness: 0.3, metalness: 0.5 })
    );
    signBoard.position.set(0, 5.6, 13.5);
    group.add(signBoard);

    // Glowing Gold Sign Text Backing
    const signGlow = new THREE.Mesh(
      new THREE.BoxGeometry(15, 1.3, 0.5),
      this.materials.goldAccent
    );
    signGlow.position.set(0, 5.6, 13.52);
    group.add(signGlow);

    this.scene.add(group);
    this.registerEntity(group, {
      id: "lobby",
      name: "Main Bank Lobby",
      type: "building",
      details: "Grand Vegas-style open marble banking hall with neoclassical columns and teller stations.",
      cameraTarget: new THREE.Vector3(0, 2, 2),
      cameraPos: new THREE.Vector3(14, 18, 18),
    });
  }

  // 2. TELLER COUNTER
  buildTellerCounter() {
    const group = new THREE.Group();
    group.name = "TellerCounter";
    group.position.set(0, 0, 1);

    // Main curved security counter desk
    const deskGeo = new THREE.BoxGeometry(18, 2.2, 3);
    const desk = new THREE.Mesh(deskGeo, this.materials.whiteStone);
    desk.position.set(0, 1.1, 0);
    desk.castShadow = true;
    desk.receiveShadow = true;
    group.add(desk);

    // Counter top (Black granite / polished marble)
    const topGeo = new THREE.BoxGeometry(19, 0.3, 3.4);
    const counterTop = new THREE.Mesh(
      topGeo,
      new THREE.MeshStandardMaterial({ color: 0x0F172A, roughness: 0.2, metalness: 0.5 })
    );
    counterTop.position.set(0, 2.3, 0);
    group.add(counterTop);

    // 3 Teller Windows with Security Glass & Brass Bars
    const tellerWindows = [-5.5, 0, 5.5];
    tellerWindows.forEach((x, idx) => {
      // Glass partition
      const glassPane = new THREE.Mesh(new THREE.BoxGeometry(4.8, 4, 0.2), this.materials.glass);
      glassPane.position.set(x, 4.4, 0);
      group.add(glassPane);

      // Speaking hole & transaction tray
      const tray = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.15, 1.2), this.materials.bankTrim);
      tray.position.set(x, 2.45, 0);
      group.add(tray);

      // Teller computer terminal (behind window)
      const monitor = new THREE.Mesh(
        new THREE.BoxGeometry(1.2, 0.9, 0.15),
        new THREE.MeshStandardMaterial({ color: 0x1E293B, roughness: 0.5 })
      );
      monitor.position.set(x, 3.0, -1.1);
      group.add(monitor);

      const screen = new THREE.Mesh(
        new THREE.BoxGeometry(1.0, 0.7, 0.05),
        this.materials.neonBlue
      );
      screen.position.set(x, 3.0, -1.02);
      group.add(screen);

      // Teller Window Number Plate
      const numPlate = new THREE.Mesh(
        new THREE.BoxGeometry(1.2, 0.5, 0.1),
        this.materials.bankTrim
      );
      numPlate.position.set(x, 6.6, 0.1);
      group.add(numPlate);
    });

    // Velvet queue stanchions in front of counter
    const stanchionMat = this.materials.goldAccent;
    const ropeMat = new THREE.MeshStandardMaterial({ color: 0x991B1B, roughness: 0.8 });

    const stanchionPositions = [
      [-6, 4], [-2, 4], [2, 4], [6, 4],
      [-6, 7], [-2, 7], [2, 7], [6, 7],
    ];

    stanchionPositions.forEach(([x, z]) => {
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 2.0, 8), stanchionMat);
      pole.position.set(x, 1.0, z);
      pole.castShadow = true;
      group.add(pole);

      const sphereTop = new THREE.Mesh(new THREE.SphereGeometry(0.22, 8, 8), stanchionMat);
      sphereTop.position.set(x, 2.05, z);
      group.add(sphereTop);

      const base = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.45, 0.1, 8), stanchionMat);
      base.position.set(x, 0.05, z);
      group.add(base);
    });

    // Velvet ropes connecting stanchions
    const addRope = (p1, p2) => {
      const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
      const len = p1.distanceTo(p2);
      const rope = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, len, 6), ropeMat);
      rope.position.copy(mid);
      rope.position.y -= 0.15; // Natural sag
      rope.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), p2.clone().sub(p1).normalize());
      group.add(rope);
    };

    addRope(new THREE.Vector3(-6, 1.9, 4), new THREE.Vector3(-2, 1.9, 4));
    addRope(new THREE.Vector3(2, 1.9, 4), new THREE.Vector3(6, 1.9, 4));
    addRope(new THREE.Vector3(-2, 1.9, 4), new THREE.Vector3(-2, 1.9, 7));
    addRope(new THREE.Vector3(2, 1.9, 4), new THREE.Vector3(2, 1.9, 7));

    this.scene.add(group);
    this.registerEntity(group, {
      id: "counter",
      name: "Teller Counter",
      type: "service",
      details: "High-security transaction counter where requests originate and split across vaults.",
      cameraTarget: new THREE.Vector3(0, 2, 2),
      cameraPos: new THREE.Vector3(12, 14, 18),
    });
  }

  // 3. MANAGER OFFICE (ELEVATED GLASS)
  buildManagerOffice() {
    const group = new THREE.Group();
    group.name = "ManagerOffice";
    group.position.set(-13, 0, -10);

    // Mezzanine floor slab
    const floor = new THREE.Mesh(
      new THREE.BoxGeometry(10, 0.6, 9),
      this.materials.whiteStone
    );
    floor.position.set(0, 4.0, 0);
    floor.receiveShadow = true;
    group.add(floor);

    // 4 Support pillars
    [[-4.5, -4], [4.5, -4], [-4.5, 4], [4.5, 4]].forEach(([px, pz]) => {
      const pillar = new THREE.Mesh(
        new THREE.CylinderGeometry(0.35, 0.4, 4.0, 8),
        this.materials.darkMetal
      );
      pillar.position.set(px, 2.0, pz);
      pillar.castShadow = true;
      group.add(pillar);
    });

    // Glass walls enclosure (Front and Right facing lobby)
    const glassFront = new THREE.Mesh(new THREE.BoxGeometry(9.6, 5.0, 0.15), this.materials.glass);
    glassFront.position.set(0, 6.8, 4.3);
    group.add(glassFront);

    const glassRight = new THREE.Mesh(new THREE.BoxGeometry(0.15, 5.0, 8.6), this.materials.glass);
    glassRight.position.set(4.8, 6.8, 0);
    group.add(glassRight);

    // Solid back/left privacy walls
    const solidBack = new THREE.Mesh(new THREE.BoxGeometry(9.8, 5.0, 0.4), this.materials.bankWalls);
    solidBack.position.set(0, 6.8, -4.3);
    group.add(solidBack);

    const solidLeft = new THREE.Mesh(new THREE.BoxGeometry(0.4, 5.0, 8.8), this.materials.bankWalls);
    solidLeft.position.set(-4.8, 6.8, 0);
    group.add(solidLeft);

    // Gold ceiling frame
    const ceiling = new THREE.Mesh(new THREE.BoxGeometry(10.2, 0.5, 9.2), this.materials.bankTrim);
    ceiling.position.set(0, 9.5, 0);
    group.add(ceiling);

    // Interior Furniture: Mahogany Desk
    const deskMat = new THREE.MeshStandardMaterial({ color: 0x451A03, roughness: 0.4, metalness: 0.2 });
    const desk = new THREE.Mesh(new THREE.BoxGeometry(4.0, 1.4, 2.2), deskMat);
    desk.position.set(0, 5.0, 0);
    group.add(desk);

    // Green Banker's Lamp
    const lampStem = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, 0.6, 6), this.materials.bankTrim);
    lampStem.position.set(1.4, 6.0, -0.6);
    group.add(lampStem);

    const lampShade = new THREE.Mesh(
      new THREE.CylinderGeometry(0.2, 0.35, 0.3, 6),
      new THREE.MeshStandardMaterial({ color: 0x15803D, roughness: 0.2, emissive: 0x15803D, emissiveIntensity: 0.4 })
    );
    lampShade.rotation.z = Math.PI / 2;
    lampShade.position.set(1.4, 6.3, -0.6);
    group.add(lampShade);

    // Executive Chair (Purple velvet)
    const chairMat = new THREE.MeshStandardMaterial({ color: 0x6B21A8, roughness: 0.7 });
    const chairSeat = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.3, 1.6), chairMat);
    chairSeat.position.set(0, 4.9, -1.8);
    group.add(chairSeat);

    const chairBack = new THREE.Mesh(new THREE.BoxGeometry(1.6, 2.0, 0.3), chairMat);
    chairBack.position.set(0, 6.0, -2.5);
    group.add(chairBack);

    // Wall Safe with Gold Dial
    const safe = new THREE.Mesh(
      new THREE.BoxGeometry(2.0, 2.4, 0.6),
      new THREE.MeshStandardMaterial({ color: 0x1E293B, roughness: 0.3, metalness: 0.8 })
    );
    safe.position.set(-4.4, 6.5, -1.5);
    group.add(safe);

    const dial = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 0.1, 12), this.materials.goldAccent);
    dial.rotation.z = Math.PI / 2;
    dial.position.set(-4.05, 6.5, -1.5);
    group.add(dial);

    this.scene.add(group);
    this.registerEntity(group, {
      id: "office",
      name: "Manager Office",
      type: "office",
      details: "Glass-walled mezzanine office overlooking bank operations with executive wall safe.",
      cameraTarget: new THREE.Vector3(-13, 6, -10),
      cameraPos: new THREE.Vector3(0, 16, 8),
    });
  }

  // 4. SERVER ROOM
  buildServerRoom() {
    const group = new THREE.Group();
    group.name = "ServerRoom";
    group.position.set(22, 0, -12);

    // Server room enclosure walls
    const roomGeo = new THREE.BoxGeometry(14, 9, 14);
    const room = new THREE.Mesh(roomGeo, this.materials.bankWalls);
    room.position.y = 4.5;
    room.castShadow = true;
    room.receiveShadow = true;
    group.add(room);

    // Cutout view window / security glass on west wall
    const windowGlass = new THREE.Mesh(new THREE.BoxGeometry(0.2, 5.0, 8.0), this.materials.glass);
    windowGlass.position.set(-7.05, 4.5, 0);
    group.add(windowGlass);

    // Server Racks inside
    const rackGeo = new THREE.BoxGeometry(2.0, 7.0, 1.8);
    const rackPositions = [
      [-3, -3], [0, -3], [3, -3],
      [-3, 2], [0, 2], [3, 2],
    ];

    rackPositions.forEach(([rx, rz], idx) => {
      const rack = new THREE.Mesh(rackGeo, this.materials.serverRack);
      rack.position.set(rx, 3.8, rz);
      rack.castShadow = true;
      group.add(rack);

      // Blinking status LEDs on rack face
      for (let row = 0; row < 6; row++) {
        const ledGeo = new THREE.BoxGeometry(0.1, 0.15, 0.15);
        const ledMat = new THREE.MeshBasicMaterial({
          color: (row + idx) % 2 === 0 ? 0x10B981 : 0x38BDF8,
        });
        const led = new THREE.Mesh(ledGeo, ledMat);
        led.position.set(rx - 1.02, 1.5 + row * 0.85, rz);
        group.add(led);
        this.blinkingLeds.push({ mesh: led, freq: 1.5 + ((row * 3 + idx) % 7) * 0.4 });
      }
    });

    // Overhead high-tech cooling pipes and blue data trunks
    const pipeMat = new THREE.MeshStandardMaterial({ color: 0x38BDF8, roughness: 0.3, metalness: 0.7 });
    const pipeGeo = new THREE.CylinderGeometry(0.3, 0.3, 12, 8);
    const pipe = new THREE.Mesh(pipeGeo, pipeMat);
    pipe.rotation.x = Math.PI / 2;
    pipe.position.set(0, 8.0, 0);
    group.add(pipe);

    // Data cable bridge leading westward across hallway to Vault corridor
    const cableGeo = new THREE.BoxGeometry(16, 0.4, 0.8);
    const cable = new THREE.Mesh(cableGeo, this.materials.neonBlue);
    cable.position.set(-14, 8.0, -10);
    group.add(cable);

    this.animatedObjects.push((delta, time) => {
      this.blinkingLeds.forEach((item) => {
        const on = Math.sin(time * item.freq * 4) > 0.1;
        item.mesh.visible = on;
      });
    });

    this.scene.add(group);
    this.registerEntity(group, {
      id: "server_room",
      name: "Server Room",
      type: "infrastructure",
      details: "High-security core hosting Z3 Prover, PAIR Transactional Gate, and LoRA inference engines.",
      cameraTarget: new THREE.Vector3(22, 5, -12),
      cameraPos: new THREE.Vector3(38, 16, 8),
    });
  }

  // 5. VAULT HALL WITH 3 VAULT DOORS
  buildVaultHall() {
    const group = new THREE.Group();
    group.name = "VaultHall";
    group.position.set(0, 0, -32);

    // Massive reinforced concrete vault corridor wall
    const wallGeo = new THREE.BoxGeometry(64, 15, 8);
    const wall = new THREE.Mesh(wallGeo, this.materials.darkMetal);
    wall.position.y = 7.5;
    wall.castShadow = true;
    wall.receiveShadow = true;
    group.add(wall);

    // Vault Hall Header Marquee
    const headerGeo = new THREE.BoxGeometry(60, 2.0, 1.5);
    const header = new THREE.Mesh(headerGeo, this.materials.bankTrim);
    header.position.set(0, 14.5, 4.0);
    group.add(header);

    // Dramatic Vault Corridor Downlights
    const vaultLights = [
      { x: -18, color: 0xFACC15 }, // Left: Gold/Amber
      { x: 0, color: 0x38BDF8 },   // Middle: Ice Blue/Cyan
      { x: 18, color: 0x10B981 },  // Right: Emerald Green
    ];
    vaultLights.forEach(({ x, color }) => {
      const pl = new THREE.PointLight(color, 2.8, 28, 1.2);
      pl.position.set(x, 13.5, 6.0);
      group.add(pl);

      // Visible glowing downlight fixture
      const fixture = new THREE.Mesh(
        new THREE.CylinderGeometry(0.8, 0.8, 0.4, 8),
        new THREE.MeshBasicMaterial({ color })
      );
      fixture.position.set(x, 14.2, 4.8);
      group.add(fixture);
    });

    // Store vault door meshes and components for animations in vaults.js
    this.vaults = {};

    // --- VAULT 1: LEFT "LLM Judge" (Weak / Naive) ---
    const leftVaultGroup = new THREE.Group();
    leftVaultGroup.position.set(-18, 0, 4);

    // Frame
    const leftFrame = new THREE.Mesh(
      new THREE.CylinderGeometry(4.8, 5.2, 1.2, 16),
      this.materials.whiteStone
    );
    leftFrame.rotation.x = Math.PI / 2;
    leftFrame.position.y = 6;
    leftVaultGroup.add(leftFrame);

    // Door (Pivots open on step 3)
    const leftDoorPivot = new THREE.Group();
    leftDoorPivot.position.set(-4.2, 6, 0.6);

    const leftDoor = new THREE.Mesh(
      new THREE.CylinderGeometry(4.2, 4.2, 0.8, 16),
      new THREE.MeshStandardMaterial({ color: 0x94A3B8, roughness: 0.5, metalness: 0.4 })
    );
    leftDoor.rotation.x = Math.PI / 2;
    leftDoor.position.set(4.2, 0, 0);
    leftDoorPivot.add(leftDoor);

    // Golden lock handle
    const leftHandle = new THREE.Mesh(
      new THREE.TorusGeometry(1.2, 0.25, 8, 16),
      this.materials.goldAccent
    );
    leftHandle.position.set(4.2, 0, 0.6);
    leftDoorPivot.add(leftHandle);

    leftVaultGroup.add(leftDoorPivot);

    // Digital SAFE% Display panel above door
    const safeDisplay = new THREE.Mesh(
      new THREE.BoxGeometry(6.5, 1.8, 0.4),
      new THREE.MeshStandardMaterial({ color: 0x0A0F1D, roughness: 0.2 })
    );
    safeDisplay.position.set(0, 11.8, 0.2);
    leftVaultGroup.add(safeDisplay);

    // Canvas for dynamic SAFE% rolling ticker
    const safeCanvas = document.createElement('canvas');
    safeCanvas.width = 256;
    safeCanvas.height = 80;
    const safeCtx = safeCanvas.getContext('2d');
    safeCtx.fillStyle = '#0B0F1E';
    safeCtx.fillRect(0, 0, 256, 80);
    safeCtx.fillStyle = '#FACC15';
    safeCtx.font = 'bold 36px monospace';
    safeCtx.textAlign = 'center';
    safeCtx.fillText('SAFE: 99%', 128, 52);

    const safeTexture = new THREE.CanvasTexture(safeCanvas);
    const safeScreen = new THREE.Mesh(
      new THREE.PlaneGeometry(6.0, 1.5),
      new THREE.MeshBasicMaterial({ map: safeTexture })
    );
    safeScreen.position.set(0, 11.8, 0.42);
    leftVaultGroup.add(safeScreen);

    // Name Plate
    const leftLabel = this.createPlateMesh('① LLM JUDGE (WEAK)', 0xFACC15);
    leftLabel.position.set(0, 13.2, 0.3);
    leftVaultGroup.add(leftLabel);

    group.add(leftVaultGroup);
    this.vaults.left = {
      group: leftVaultGroup,
      pivot: leftDoorPivot,
      canvas: safeCanvas,
      ctx: safeCtx,
      texture: safeTexture,
    };

    // --- VAULT 2: MIDDLE "Kill-Switch" (Rigid / Lockdown) ---
    const midVaultGroup = new THREE.Group();
    midVaultGroup.position.set(0, 0, 4);

    // Heavy Titanium Bunker Frame
    const midFrame = new THREE.Mesh(
      new THREE.CylinderGeometry(5.2, 5.6, 1.8, 12),
      this.materials.darkMetal
    );
    midFrame.rotation.x = Math.PI / 2;
    midFrame.position.y = 6;
    midVaultGroup.add(midFrame);

    // Massive blast door
    const midDoor = new THREE.Mesh(
      new THREE.CylinderGeometry(4.6, 4.6, 1.2, 12),
      new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.3, metalness: 0.85 })
    );
    midDoor.rotation.x = Math.PI / 2;
    midDoor.position.set(0, 6, 0.4);
    midVaultGroup.add(midDoor);

    // Giant 6-spoke locking wheel
    const wheelHub = new THREE.Mesh(new THREE.CylinderGeometry(0.8, 0.8, 0.6, 12), this.materials.goldAccent);
    wheelHub.rotation.x = Math.PI / 2;
    wheelHub.position.set(0, 6, 1.2);
    midVaultGroup.add(wheelHub);

    for (let s = 0; s < 6; s++) {
      const spoke = new THREE.Mesh(new THREE.BoxGeometry(0.3, 3.4, 0.3), this.materials.darkMetal);
      spoke.rotation.z = (s * Math.PI) / 3;
      spoke.position.set(0, 6, 1.2);
      midVaultGroup.add(spoke);
    }

    // Overhead Red Emergency Revolving Strobe Light
    const sirenBase = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 1.1, 0.6, 12), this.materials.darkMetal);
    sirenBase.position.set(0, 12.0, 0.2);
    midVaultGroup.add(sirenBase);

    const sirenDome = new THREE.Mesh(
      new THREE.SphereGeometry(0.7, 12, 12, 0, Math.PI * 2, 0, Math.PI / 2),
      new THREE.MeshStandardMaterial({ color: 0xEF4444, emissive: 0xDC2626, emissiveIntensity: 0.8, transparent: true, opacity: 0.85 })
    );
    sirenDome.position.set(0, 12.3, 0.2);
    midVaultGroup.add(sirenDome);

    // Drop-down steel security gate (Descends on Step 4)
    const dropGateGeo = new THREE.BoxGeometry(8.5, 9.5, 0.4);
    const dropGateMat = new THREE.MeshStandardMaterial({
      color: 0x1E293B,
      roughness: 0.6,
      metalness: 0.5,
    });
    const dropGate = new THREE.Mesh(dropGateGeo, dropGateMat);
    dropGate.position.set(0, 15.5, 1.8); // Hidden above, drops to y=6.0
    midVaultGroup.add(dropGate);

    // Name Plate
    const midLabel = this.createPlateMesh('② KILL-SWITCH (RIGID)', 0x38BDF8);
    midLabel.position.set(0, 13.2, 0.3);
    midVaultGroup.add(midLabel);

    group.add(midVaultGroup);
    this.vaults.middle = {
      group: midVaultGroup,
      siren: sirenDome,
      dropGate: dropGate,
      door: midDoor,
    };

    // --- VAULT 3: RIGHT "PAIR Gate" (Surgical High-Tech) ---
    const rightVaultGroup = new THREE.Group();
    rightVaultGroup.position.set(18, 0, 4);

    // High-tech hexagonal gate frame
    const rightFrame = new THREE.Mesh(
      new THREE.CylinderGeometry(5.2, 5.6, 1.6, 6),
      this.materials.bankTrim
    );
    rightFrame.rotation.x = Math.PI / 2;
    rightFrame.position.y = 6;
    rightVaultGroup.add(rightFrame);

    // Dual-split surgical blast doors (Top and Bottom guillotine leaves)
    const upperDoor = new THREE.Mesh(
      new THREE.BoxGeometry(7.2, 4.4, 0.9),
      new THREE.MeshStandardMaterial({ color: 0x1E293B, roughness: 0.3, metalness: 0.7 })
    );
    upperDoor.position.set(0, 8.2, 0.6);
    rightVaultGroup.add(upperDoor);

    const lowerDoor = new THREE.Mesh(
      new THREE.BoxGeometry(7.2, 4.4, 0.9),
      new THREE.MeshStandardMaterial({ color: 0x1E293B, roughness: 0.3, metalness: 0.7 })
    );
    lowerDoor.position.set(0, 3.8, 0.6);
    rightVaultGroup.add(lowerDoor);

    // Vertical emerald laser validation beam in center
    const laserBeam = new THREE.Mesh(
      new THREE.CylinderGeometry(0.1, 0.1, 8.5, 8),
      this.materials.neonGreen
    );
    laserBeam.position.set(0, 6, 1.2);
    rightVaultGroup.add(laserBeam);

    // Shunt chute connecting to Shredder Plant on right
    const shuntTube = new THREE.Mesh(
      new THREE.CylinderGeometry(0.8, 0.8, 8.5, 8),
      new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.5, metalness: 0.6 })
    );
    shuntTube.rotation.z = Math.PI / 2;
    shuntTube.position.set(5.5, 6.0, 0.6);
    rightVaultGroup.add(shuntTube);

    // Name Plate
    const rightLabel = this.createPlateMesh('③ PAIR GATE (SURGICAL)', 0x10B981);
    rightLabel.position.set(0, 13.2, 0.3);
    rightVaultGroup.add(rightLabel);

    group.add(rightVaultGroup);
    this.vaults.right = {
      group: rightVaultGroup,
      upperDoor,
      lowerDoor,
      laser: laserBeam,
    };

    // --- FRAMED POSTER INSIDE VAULT HALL ---
    const posterGroup = new THREE.Group();
    posterGroup.position.set(9, 7.0, 4.05);

    // Elegant gold frame
    const frameGeo = new THREE.BoxGeometry(4.2, 5.6, 0.25);
    const frameMat = new THREE.MeshStandardMaterial({
      color: 0xF59E0B,
      metalness: 0.85,
      roughness: 0.25,
    });
    const frameMesh = new THREE.Mesh(frameGeo, frameMat);
    posterGroup.add(frameMesh);

    // Dark matting backing
    const mattingGeo = new THREE.BoxGeometry(3.8, 5.2, 0.08);
    const mattingMat = new THREE.MeshStandardMaterial({ color: 0x0B0F1E, roughness: 0.8 });
    const mattingMesh = new THREE.Mesh(mattingGeo, mattingMat);
    mattingMesh.position.z = 0.1;
    posterGroup.add(mattingMesh);

    // Poster surface plane
    const photoPlaneGeo = new THREE.PlaneGeometry(3.5, 4.8);
    const photoPlaneMat = new THREE.MeshBasicMaterial({
      map: createAvatarTexture(),
    });
    this.vaultPosterMesh = new THREE.Mesh(photoPlaneGeo, photoPlaneMat);
    this.vaultPosterMesh.position.z = 0.15;
    posterGroup.add(this.vaultPosterMesh);

    // Header plaque above poster
    const plaqueMesh = this.createPlateMesh('★ SUSPECT DOSSIER ★', 0xF59E0B);
    plaqueMesh.scale.set(0.72, 0.72, 1);
    plaqueMesh.position.set(0, 3.2, 0.16);
    posterGroup.add(plaqueMesh);

    // Dedicated gallery spotlight on the framed poster
    const posterLight = new THREE.SpotLight(0xFFFBEB, 3.2, 24, Math.PI / 4, 0.35);
    posterLight.position.set(9, 13.5, 8.5);
    posterLight.target.position.set(9, 7.0, 4.1);
    group.add(posterLight);
    group.add(posterLight.target);

    group.add(posterGroup);

    this.scene.add(group);
    this.registerEntity(group, {
      id: "vault_hall",
      name: "Vault Hall",
      type: "vault",
      details: "Triple-vault proving corridor: Left LLM Judge, Middle Kill-Switch, and Right PAIR Gate.",
      cameraTarget: new THREE.Vector3(0, 6, -28),
      cameraPos: new THREE.Vector3(0, 18, -6),
    });
  }

  // Helper to generate crisp 3D text/plate labels
  createPlateMesh(text, colorHex) {
    const canvas = document.createElement('canvas');
    canvas.width = 384;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#0B0F1E';
    ctx.fillRect(0, 0, 384, 64);
    ctx.strokeStyle = `#${colorHex.toString(16).padStart(6, '0')}`;
    ctx.lineWidth = 4;
    ctx.strokeRect(2, 2, 380, 60);
    ctx.fillStyle = `#${colorHex.toString(16).padStart(6, '0')}`;
    ctx.font = 'bold 26px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 192, 32);

    const texture = new THREE.CanvasTexture(canvas);
    const mesh = new THREE.Mesh(
      new THREE.PlaneGeometry(6.4, 1.1),
      new THREE.MeshBasicMaterial({ map: texture, transparent: true })
    );
    return mesh;
  }

  // 6. SHREDDER PLANT
  buildShredderPlant() {
    const group = new THREE.Group();
    group.name = "ShredderPlant";
    group.position.set(32, 0, -28);

    // Industrial plant building enclosure
    const plantGeo = new THREE.BoxGeometry(16, 12, 16);
    const plant = new THREE.Mesh(plantGeo, this.materials.shredderSteel);
    plant.position.y = 6.0;
    plant.castShadow = true;
    plant.receiveShadow = true;
    group.add(plant);

    // Sloped industrial roof
    const roofGeo = new THREE.ConeGeometry(12, 4, 4);
    const roof = new THREE.Mesh(roofGeo, this.materials.darkMetal);
    roof.rotation.y = Math.PI / 4;
    roof.position.set(0, 14.0, 0);
    group.add(roof);

    // Twin smokestacks
    [-3, 3].forEach((x) => {
      const stack = new THREE.Mesh(
        new THREE.CylinderGeometry(0.7, 0.9, 7, 8),
        this.materials.darkMetal
      );
      stack.position.set(x, 15.5, -2);
      group.add(stack);
    });

    // Visible Shredder Hopper bay at front with hazard stripes
    const hopperFrame = new THREE.Mesh(
      new THREE.BoxGeometry(8, 5, 4),
      new THREE.MeshStandardMaterial({ color: 0xFACC15, roughness: 0.5 })
    );
    hopperFrame.position.set(0, 3.5, 8.2);
    group.add(hopperFrame);

    // Twin counter-rotating toothed cylinders (Visible in hopper)
    const drumMat = new THREE.MeshStandardMaterial({ color: 0x94A3B8, roughness: 0.3, metalness: 0.9 });
    const drumGeo = new THREE.CylinderGeometry(0.9, 0.9, 5.0, 10);

    const drumL = new THREE.Mesh(drumGeo, drumMat);
    drumL.rotation.z = Math.PI / 2;
    drumL.position.set(0, 3.5, 7.2);
    group.add(drumL);

    const drumR = new THREE.Mesh(drumGeo, drumMat);
    drumR.rotation.z = Math.PI / 2;
    drumR.position.set(0, 3.5, 9.2);
    group.add(drumR);

    // Hazard Stripes Board
    const hazardStripe = new THREE.Mesh(
      new THREE.BoxGeometry(8, 0.8, 0.2),
      this.materials.bankTrim
    );
    hazardStripe.position.set(0, 6.2, 10.3);
    group.add(hazardStripe);

    // Red Laser Cutting Array emitters
    for (let l = -2; l <= 2; l += 2) {
      const laser = new THREE.Mesh(
        new THREE.CylinderGeometry(0.04, 0.04, 3.2, 6),
        this.materials.neonRed
      );
      laser.position.set(l, 3.5, 8.2);
      group.add(laser);
    }

    this.animatedObjects.push((delta) => {
      drumL.rotation.x += delta * 6;
      drumR.rotation.x -= delta * 6;
    });

    this.scene.add(group);
    this.registerEntity(group, {
      id: "shredder",
      name: "Shredder Plant",
      type: "security",
      details: "Industrial transaction shredder that incinerates unauthorized red rows in real time.",
      cameraTarget: new THREE.Vector3(32, 5, -28),
      cameraPos: new THREE.Vector3(46, 16, -10),
    });
  }

  // 7. CASINO JACKPOT TOWER WITH ANIMATED TICKER
  buildCasinoJackpotTower() {
    const group = new THREE.Group();
    group.name = "CasinoJackpotTower";
    group.position.set(-36, 0, 14);

    // Stepped art-deco casino obelisk
    const tiers = [
      { w: 12, h: 4, d: 12, y: 2 },
      { w: 9.5, h: 10, d: 9.5, y: 9 },
      { w: 7.5, h: 14, d: 7.5, y: 21 },
      { w: 5.5, h: 10, d: 5.5, y: 33 },
      { w: 3.5, h: 6, d: 3.5, y: 41 },
    ];

    tiers.forEach((t) => {
      const geo = new THREE.BoxGeometry(t.w, t.h, t.d);
      const mesh = new THREE.Mesh(geo, this.materials.bankWalls);
      mesh.position.y = t.y;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      group.add(mesh);

      // Gold crown moulding for each tier
      const trimGeo = new THREE.BoxGeometry(t.w + 0.6, 0.4, t.d + 0.6);
      const trim = new THREE.Mesh(trimGeo, this.materials.bankTrim);
      trim.position.y = t.y + t.h / 2;
      group.add(trim);
    });

    // Glowing Neon Jackpot Crown at top
    const crownGeo = new THREE.ConeGeometry(2.5, 5, 8);
    const crown = new THREE.Mesh(crownGeo, this.materials.goldAccent);
    crown.position.y = 46.5;
    group.add(crown);

    const spire = new THREE.Mesh(
      new THREE.CylinderGeometry(0.1, 0.3, 8, 6),
      this.materials.bankTrim
    );
    spire.position.y = 50.5;
    group.add(spire);

    // GIANT 4-SIDED SCROLLING LED MATRIX TICKER DISPLAY
    const tickerW = 2048;
    const tickerH = 128;
    this.tickerCanvas = document.createElement('canvas');
    this.tickerCanvas.width = tickerW;
    this.tickerCanvas.height = tickerH;
    this.tickerCtx = this.tickerCanvas.getContext('2d');

    this.tickerTexture = new THREE.CanvasTexture(this.tickerCanvas);
    this.tickerTexture.wrapS = THREE.RepeatWrapping;
    this.tickerTexture.wrapT = THREE.ClampToEdgeWrapping;

    const tickerMat = new THREE.MeshBasicMaterial({ map: this.tickerTexture });

    // 4 Display faces on the tower
    const faceW = 7.6;
    const faceH = 5.2;
    const faceY = 21;

    const faces = [
      { r: 0, p: [0, faceY, 3.85] },
      { r: Math.PI / 2, p: [3.85, faceY, 0] },
      { r: Math.PI, p: [0, faceY, -3.85] },
      { r: -Math.PI / 2, p: [-3.85, faceY, 0] },
    ];

    faces.forEach((f) => {
      const panel = new THREE.Mesh(new THREE.PlaneGeometry(faceW, faceH), tickerMat);
      panel.rotation.y = f.r;
      panel.position.set(...f.p);
      group.add(panel);
    });

    // Render initial ticker frame
    this.updateTickerText('🎰 JACKPOT: $5,000,000.00  •  ⚡ PAIR KERNEL 1.4ms GATE  •  🚨 HEISTGUARD-LoRA ACTIVE  •  🪙 HONEST $25.00 REFUND PROTECTED  •  ');

    this.animatedObjects.push((delta) => {
      this.tickerOffset += delta * 0.15;
      this.tickerTexture.offset.x = this.tickerOffset % 1.0;
    });

    this.scene.add(group);
    this.registerEntity(group, {
      id: "tower",
      name: "Casino Jackpot Tower",
      type: "landmark",
      details: "Iconic Las Vegas neon jackpot obelisk with a live scrolling LED marquee.",
      cameraTarget: new THREE.Vector3(-36, 22, 14),
      cameraPos: new THREE.Vector3(-14, 34, 44),
    });
  }

  updateTickerText(text) {
    if (!this.tickerCtx) return;
    const ctx = this.tickerCtx;
    ctx.fillStyle = '#080C18';
    ctx.fillRect(0, 0, 2048, 128);

    // Matrix LED dot effect
    ctx.fillStyle = '#FFC93C';
    ctx.font = 'bold 54px monospace';
    ctx.textBaseline = 'middle';
    ctx.fillText(text.repeat(2), 20, 64);

    if (this.tickerTexture) {
      this.tickerTexture.needsUpdate = true;
    }
  }

  // 8. POLICE STATION
  buildPoliceStation() {
    const group = new THREE.Group();
    group.name = "PoliceStation";
    group.position.set(34, 0, 18);

    // Main precinct building
    const baseGeo = new THREE.BoxGeometry(22, 10, 18);
    const building = new THREE.Mesh(baseGeo, this.materials.bankWalls);
    building.position.y = 5.0;
    building.castShadow = true;
    building.receiveShadow = true;
    group.add(building);

    // Blue Police Banner Stripe
    const stripe = new THREE.Mesh(
      new THREE.BoxGeometry(22.2, 1.2, 18.2),
      new THREE.MeshStandardMaterial({ color: COLORS.policeBlue, roughness: 0.4 })
    );
    stripe.position.y = 8.5;
    group.add(stripe);

    // Rooftop Helipad
    const padGeo = new THREE.BoxGeometry(16, 0.4, 14);
    const pad = new THREE.Mesh(padGeo, this.materials.darkMetal);
    pad.position.y = 10.2;
    group.add(pad);

    // Helipad Yellow Circle & "H" Marking
    const hCanvas = document.createElement('canvas');
    hCanvas.width = 256;
    hCanvas.height = 256;
    const hCtx = hCanvas.getContext('2d');
    hCtx.fillStyle = '#1E293B';
    hCtx.fillRect(0, 0, 256, 256);
    hCtx.strokeStyle = '#FACC15';
    hCtx.lineWidth = 14;
    hCtx.beginPath();
    hCtx.arc(128, 128, 95, 0, Math.PI * 2);
    hCtx.stroke();
    hCtx.fillStyle = '#FACC15';
    hCtx.font = 'bold 120px sans-serif';
    hCtx.textAlign = 'center';
    hCtx.textBaseline = 'middle';
    hCtx.fillText('H', 128, 134);

    const hTexture = new THREE.CanvasTexture(hCanvas);
    const hMesh = new THREE.Mesh(
      new THREE.PlaneGeometry(12, 10),
      new THREE.MeshBasicMaterial({ map: hTexture })
    );
    hMesh.rotation.x = -Math.PI / 2;
    hMesh.position.set(0, 10.42, 0);
    group.add(hMesh);

    // Radio Antenna Mast with flashing beacon
    const mast = new THREE.Mesh(
      new THREE.CylinderGeometry(0.1, 0.2, 12, 6),
      this.materials.bankTrim
    );
    mast.position.set(7, 16.0, -6);
    group.add(mast);

    const beacon = new THREE.Mesh(new THREE.SphereGeometry(0.3, 8, 8), this.materials.neonRed);
    beacon.position.set(7, 22.0, -6);
    group.add(beacon);

    // Emergency vehicle bay / garage doors
    for (let b = -5; b <= 5; b += 10) {
      const bayDoor = new THREE.Mesh(
        new THREE.BoxGeometry(6, 4.5, 0.2),
        new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.6 })
      );
      bayDoor.position.set(b, 2.3, 9.1);
      group.add(bayDoor);
    }

    this.scene.add(group);
    this.registerEntity(group, {
      id: "police_station",
      name: "Police Station",
      type: "law_enforcement",
      details: "Metropolitan Police Precinct with rooftop search & rescue helipad.",
      cameraTarget: new THREE.Vector3(34, 6, 18),
      cameraPos: new THREE.Vector3(50, 18, 38),
    });
  }

  // 9. GETAWAY GARAGE
  buildGetawayGarage() {
    const group = new THREE.Group();
    group.name = "GetawayGarage";
    group.position.set(-36, 0, -22);

    // Grimy back-alley garage building
    const garageGeo = new THREE.BoxGeometry(16, 8, 16);
    const garage = new THREE.Mesh(garageGeo, this.materials.darkMetal);
    garage.position.y = 4.0;
    garage.castShadow = true;
    garage.receiveShadow = true;
    group.add(garage);

    // Corrugated roll-up metal bay door
    const doorMat = new THREE.MeshStandardMaterial({
      color: 0x475569,
      roughness: 0.7,
      metalness: 0.6,
    });
    const bayDoor = new THREE.Mesh(new THREE.BoxGeometry(10, 6, 0.2), doorMat);
    bayDoor.position.set(0, 3.0, 8.1);
    group.add(bayDoor);

    // Alleyway Props: Oil drums
    const drumMat = new THREE.MeshStandardMaterial({ color: 0xDC2626, roughness: 0.5 });
    const drumGeo = new THREE.CylinderGeometry(0.6, 0.6, 1.6, 8);
    [[-6, 10], [-4.5, 10], [-5.2, 11.5]].forEach(([dx, dz]) => {
      const drum = new THREE.Mesh(drumGeo, drumMat);
      drum.position.set(dx, 0.8, dz);
      drum.castShadow = true;
      group.add(drum);
    });

    // Dumpster & Wooden crates
    const crateMat = new THREE.MeshStandardMaterial({ color: 0x78350F, roughness: 0.8 });
    const crateGeo = new THREE.BoxGeometry(1.6, 1.6, 1.6);
    const crate = new THREE.Mesh(crateGeo, crateMat);
    crate.position.set(6, 0.8, 10);
    crate.castShadow = true;
    group.add(crate);

    // Tire skid marks leading from garage out to perimeter road
    const skidMat = new THREE.MeshBasicMaterial({ color: 0x05070D, transparent: true, opacity: 0.75 });
    [-1.2, 1.2].forEach((tx) => {
      const skid = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 18), skidMat);
      skid.rotation.x = -Math.PI / 2;
      skid.position.set(tx, 0.12, 16);
      group.add(skid);
    });

    this.scene.add(group);
    this.registerEntity(group, {
      id: "garage",
      name: "Getaway Garage",
      type: "safehouse",
      details: "Back-alley garage hideout where the getaway van waits for loot drops.",
      cameraTarget: new THREE.Vector3(-36, 4, -22),
      cameraPos: new THREE.Vector3(-20, 16, -4),
    });
  }

  // 12. ROOFTOP IPHONE ENCLAVE STAND
  buildiPhoneEnclaveStand() {
    const group = new THREE.Group();
    group.name = "iPhoneEnclaveStand";
    group.position.set(0, 7.8, -6);

    // Elevated Rooftop Platform Base
    const platform = new THREE.Mesh(
      new THREE.CylinderGeometry(3.2, 3.8, 1.0, 16),
      this.materials.whiteStone
    );
    platform.position.y = 0.5;
    platform.castShadow = true;
    group.add(platform);

    const platformTrim = new THREE.Mesh(
      new THREE.CylinderGeometry(3.3, 3.3, 0.2, 16),
      this.materials.bankTrim
    );
    platformTrim.position.y = 1.0;
    group.add(platformTrim);

    // Pedestal
    const pedestal = new THREE.Mesh(
      new THREE.CylinderGeometry(1.4, 1.8, 1.6, 8),
      this.materials.goldAccent
    );
    pedestal.position.y = 1.8;
    pedestal.castShadow = true;
    group.add(pedestal);

    // Sleek iPhone model (Scale ~ 2.5 units tall)
    const phoneBody = new THREE.Mesh(
      new THREE.BoxGeometry(1.5, 2.8, 0.16),
      new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.2, metalness: 0.8 })
    );
    phoneBody.rotation.x = -Math.PI / 6; // Angled for viewing
    phoneBody.position.set(0, 3.4, 0);
    group.add(phoneBody);

    // Screen with glowing Face ID biometric icon
    const screenGeo = new THREE.PlaneGeometry(1.35, 2.6);
    const faceIdCanvas = document.createElement('canvas');
    faceIdCanvas.width = 128;
    faceIdCanvas.height = 256;
    const fCtx = faceIdCanvas.getContext('2d');
    fCtx.fillStyle = '#0F172A';
    fCtx.fillRect(0, 0, 128, 256);
    // Draw Face ID smiley glyph
    fCtx.strokeStyle = '#10B981';
    fCtx.lineWidth = 6;
    fCtx.strokeRect(20, 40, 88, 100);
    fCtx.fillStyle = '#10B981';
    fCtx.font = 'bold 18px monospace';
    fCtx.textAlign = 'center';
    fCtx.fillText('ENCLAVE', 64, 180);
    fCtx.font = 'bold 22px monospace';
    fCtx.fillText('FACE ID', 64, 210);

    const faceIdTex = new THREE.CanvasTexture(faceIdCanvas);
    const phoneScreen = new THREE.Mesh(
      screenGeo,
      new THREE.MeshBasicMaterial({ map: faceIdTex })
    );
    phoneScreen.position.set(0, 0, 0.09);
    phoneBody.add(phoneScreen);

    // Holographic Apple Secure Enclave hovering halo ring
    const haloGeo = new THREE.RingGeometry(1.2, 1.4, 32);
    const halo = new THREE.Mesh(
      haloGeo,
      new THREE.MeshBasicMaterial({ color: 0x10B981, side: THREE.DoubleSide, transparent: true, opacity: 0.8 })
    );
    halo.rotation.x = Math.PI / 2;
    halo.position.set(0, 5.2, 0);
    group.add(halo);

    // Golden transaction tray slot (Receives the honest $25)
    const trayGeo = new THREE.BoxGeometry(2.0, 0.3, 1.4);
    const tray = new THREE.Mesh(trayGeo, this.materials.goldAccent);
    tray.position.set(0, 2.4, 1.0);
    group.add(tray);

    this.animatedObjects.push((delta, time) => {
      halo.rotation.z += delta * 1.5;
      halo.position.y = 5.2 + Math.sin(time * 3) * 0.15;
    });

    this.scene.add(group);
    this.registerEntity(group, {
      id: "enclave_stand",
      name: "Rooftop iPhone Enclave Stand",
      type: "biometric",
      details: "Hardware Enclave authorization station requiring Apple Face ID ECDSA P-256 settlement.",
      cameraTarget: new THREE.Vector3(0, 10, -6),
      cameraPos: new THREE.Vector3(12, 18.0, 6.0),
    });
  }

  // Campus decorative environment: Streetlights, Palm trees, Plaza Fountain
  buildEnvironmentProps() {
    const group = new THREE.Group();
    group.name = "EnvironmentProps";

    // 1. Central Plaza Fountain
    const fountainBase = new THREE.Mesh(
      new THREE.CylinderGeometry(4.5, 5.0, 1.2, 16),
      this.materials.whiteStone
    );
    fountainBase.position.set(0, 0.6, 26);
    group.add(fountainBase);

    const fountainWater = new THREE.Mesh(
      new THREE.CylinderGeometry(4.2, 4.2, 0.8, 16),
      new THREE.MeshStandardMaterial({ color: 0x0284C7, roughness: 0.1, transparent: true, opacity: 0.75 })
    );
    fountainWater.position.set(0, 0.9, 26);
    group.add(fountainWater);

    const fountainCenter = new THREE.Mesh(
      new THREE.CylinderGeometry(0.8, 1.2, 3.2, 8),
      this.materials.whiteStone
    );
    fountainCenter.position.set(0, 2.0, 26);
    group.add(fountainCenter);

    // 2. Low-Poly Vegas Palm Trees
    const palmPositions = [
      [-14, 12], [14, 12],
      [-24, 28], [24, 28],
      [-26, 42], [26, 42],
    ];

    const trunkMat = new THREE.MeshStandardMaterial({ color: 0x78350F, roughness: 0.9 });
    const leafMat = new THREE.MeshStandardMaterial({ color: 0x15803D, roughness: 0.7 });

    palmPositions.forEach(([px, pz]) => {
      const tree = new THREE.Group();
      tree.position.set(px, 0, pz);

      // Curved segmented trunk
      for (let s = 0; s < 5; s++) {
        const seg = new THREE.Mesh(new THREE.CylinderGeometry(0.4 - s * 0.04, 0.45 - s * 0.04, 1.6, 6), trunkMat);
        seg.position.set(Math.sin(s * 0.2) * 0.3, 0.8 + s * 1.5, 0);
        seg.rotation.z = s * 0.05;
        seg.castShadow = true;
        tree.add(seg);
      }

      // Fronds (Fan of low-poly leaves)
      for (let i = 0; i < 6; i++) {
        const leaf = new THREE.Mesh(new THREE.ConeGeometry(1.2, 4.5, 4), leafMat);
        leaf.rotation.z = Math.PI / 3;
        leaf.rotation.y = (i * Math.PI) / 3;
        leaf.position.set(0.6, 8.2, 0);
        leaf.castShadow = true;
        tree.add(leaf);
      }
      group.add(tree);
    });

    // 3. Street Lamps with glowing orbs
    const lampMat = this.materials.darkMetal;
    const orbMat = new THREE.MeshBasicMaterial({ color: 0xFFFBEB });

    const lampPositions = [
      [-10, 16], [10, 16],
      [-10, 36], [10, 36],
      [-42, 46], [42, 46],
      [-42, -46], [42, -46],
    ];

    lampPositions.forEach(([lx, lz]) => {
      const post = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.16, 6, 6), lampMat);
      post.position.set(lx, 3, lz);
      post.castShadow = true;
      group.add(post);

      const lampHead = new THREE.Mesh(new THREE.SphereGeometry(0.4, 8, 8), orbMat);
      lampHead.position.set(lx, 6.2, lz);
      group.add(lampHead);

      // Point light for night illumination
      const light = new THREE.PointLight(0xFFE4A0, 1.2, 14, 2);
      light.position.set(lx, 6.0, lz);
      group.add(light);
    });

    this.scene.add(group);
  }

  registerEntity(object3D, meta) {
    object3D.userData = {
      isEntity: true,
      ...meta,
    };
    this.landmarks[meta.id] = object3D;
    this.interactiveEntities.push(object3D);
  }

  setVaultPosterPhoto(texture) {
    if (this.vaultPosterMesh) {
      this.vaultPosterMesh.material.map = texture;
      this.vaultPosterMesh.material.needsUpdate = true;
    }
  }

  update(delta, time) {
    this.animatedObjects.forEach((fn) => fn(delta, time));
  }
}
