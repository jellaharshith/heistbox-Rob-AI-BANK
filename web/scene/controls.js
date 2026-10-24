/**
 * HeistBox 3D Scene - Controls, Entity Selection, Camera Navigation & Cinematic Tour
 * Features:
 * - Smooth Isometric Camera Controller (Pan, Rotate, Zoom)
 * - Click Raycaster with Selection Ring, Tracking & onSelect(entity) Callback
 * - flyToArea(name) smooth interpolation (Lobby, Vault Hall, Server Room, Shredder & Garage, Casino Tower)
 * - Cinematic Mode Tour (automatically glides between areas, cancels on user interaction)
 * - Optional 2D HUD Mini-Map
 */

import * as THREE from './three.module.js';

export class SceneControls {
  constructor(camera, domElement, scene, worldManager, onSelectCallback) {
    this.camera = camera;
    this.domElement = domElement;
    this.scene = scene;
    this.worldManager = worldManager;
    this.onSelect = onSelectCallback || (() => {});

    // Target look-at point & camera offset
    this.target = new THREE.Vector3(0, 4, 0);
    this.currentPos = camera.position.clone();
    this.currentTarget = this.target.clone();

    // Smooth gliding state
    this.isTransitioning = false;
    this.transitionStartPos = new THREE.Vector3();
    this.transitionEndPos = new THREE.Vector3();
    this.transitionStartTarget = new THREE.Vector3();
    this.transitionEndTarget = new THREE.Vector3();
    this.transitionProgress = 1.0;
    this.transitionDuration = 1.2;

    // Follow selected entity
    this.followedEntity = null;
    this.selectedEntity = null;

    // Selection Indicator Ring
    this.selectionRing = this.createSelectionRing();
    this.scene.add(this.selectionRing);

    // Mouse / Touch Interaction State
    this.isDragging = false;
    this.dragButton = -1; // 0 = pan, 2 = rotate
    this.lastMouseX = 0;
    this.lastMouseY = 0;

    // Spherical orbit angles
    this.spherical = new THREE.Spherical();
    this.spherical.setFromVector3(this.camera.position.clone().sub(this.target));

    // Zoom limits
    this.minRadius = 18;
    this.maxRadius = 110;

    // Cinematic Tour Mode
    this.cinematic = false;
    this.cinematicTime = 0;
    this.cinematicWaypoints = [
      { target: new THREE.Vector3(0, 3, 10), offset: new THREE.Vector3(22, 20, 32) },    // Plaza / Lobby Front
      { target: new THREE.Vector3(0, 2, 2), offset: new THREE.Vector3(14, 16, 20) },      // Teller Counter
      { target: new THREE.Vector3(-18, 5, -26), offset: new THREE.Vector3(16, 18, 16) }, // Left Vault (LLM Judge)
      { target: new THREE.Vector3(0, 5, -26), offset: new THREE.Vector3(18, 20, 16) },     // Middle Vault (Kill-Switch)
      { target: new THREE.Vector3(18, 5, -26), offset: new THREE.Vector3(16, 18, 16) },   // Right Vault (PAIR Gate)
      { target: new THREE.Vector3(32, 5, -28), offset: new THREE.Vector3(20, 18, 16) },  // Shredder Plant
      { target: new THREE.Vector3(0, 8, -19.5), offset: new THREE.Vector3(14, 16, 16) },  // Rooftop iPhone Enclave
      { target: new THREE.Vector3(-36, 20, 14), offset: new THREE.Vector3(20, 22, 28) }, // Casino Jackpot Tower
    ];

    // Raycaster for entity clicking
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();

    this.initEventListeners();
  }

  createSelectionRing() {
    const ringGeo = new THREE.RingGeometry(1.6, 1.9, 32);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0xFFC93C,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.85,
    });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.15;
    ring.visible = false;
    return ring;
  }

  initEventListeners() {
    const el = this.domElement;

    // Prevent context menu on right click for smooth right-drag orbit
    el.addEventListener('contextmenu', (e) => e.preventDefault());

    el.addEventListener('pointerdown', (e) => {
      this.cancelCinematic();
      this.isDragging = true;
      this.dragButton = e.button;
      this.lastMouseX = e.clientX;
      this.lastMouseY = e.clientY;
      this.dragMoved = 0;
    });

    window.addEventListener('pointermove', (e) => {
      if (!this.isDragging) return;

      const dx = e.clientX - this.lastMouseX;
      const dy = e.clientY - this.lastMouseY;
      this.dragMoved += Math.abs(dx) + Math.abs(dy);

      this.lastMouseX = e.clientX;
      this.lastMouseY = e.clientY;

      if (this.dragButton === 0) {
        // Left drag: Pan along isometric ground plane
        const panSpeed = this.spherical.radius * 0.0016;

        // Calculate right and forward vectors based on camera azimuth
        const forward = new THREE.Vector3(-Math.sin(this.spherical.theta), 0, -Math.cos(this.spherical.theta));
        const right = new THREE.Vector3(Math.cos(this.spherical.theta), 0, -Math.sin(this.spherical.theta));

        this.target.addScaledVector(right, -dx * panSpeed);
        this.target.addScaledVector(forward, dy * panSpeed);
        this.followedEntity = null; // Unfollow when user manually pans
      } else if (this.dragButton === 2) {
        // Right drag: Orbit / Rotate azimuth & elevation
        const rotSpeed = 0.005;
        this.spherical.theta -= dx * rotSpeed;
        this.spherical.phi = Math.max(0.2, Math.min(Math.PI / 2 - 0.05, this.spherical.phi - dy * rotSpeed));
      }
    });

    window.addEventListener('pointerup', (e) => {
      if (this.isDragging && this.dragMoved < 6 && e.button === 0) {
        // This was a clean click without dragging: Raycast select entity
        this.handleEntityClick(e);
      }
      this.isDragging = false;
    });

    el.addEventListener('wheel', (e) => {
      e.preventDefault();
      this.cancelCinematic();
      const zoomFactor = e.deltaY > 0 ? 1.08 : 0.92;
      this.spherical.radius = THREE.MathUtils.clamp(
        this.spherical.radius * zoomFactor,
        this.minRadius,
        this.maxRadius
      );
    }, { passive: false });
  }

  handleEntityClick(e) {
    const rect = this.domElement.getBoundingClientRect();
    this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    this.raycaster.setFromCamera(this.mouse, this.camera);
    const intersects = this.raycaster.intersectObjects(this.worldManager.interactiveEntities, true);

    if (intersects.length > 0) {
      // Find parent with userData.isEntity
      let obj = intersects[0].object;
      while (obj && (!obj.userData || !obj.userData.isEntity) && obj.parent) {
        obj = obj.parent;
      }

      if (obj && obj.userData && obj.userData.isEntity) {
        this.selectEntity(obj);
      }
    } else {
      // Clicked ground: clear selection
      this.deselect();
    }
  }

  selectEntity(obj) {
    this.selectedEntity = obj;
    this.selectionRing.visible = true;

    // Ring follows entity position
    const worldPos = new THREE.Vector3();
    obj.getWorldPosition(worldPos);
    this.selectionRing.position.set(worldPos.x, 0.15, worldPos.z);

    // If character or vehicle, track it
    if (obj.userData.type === 'character' || obj.userData.type === 'vehicle') {
      this.followedEntity = obj;
    } else {
      this.followedEntity = null;
    }

    // Glide camera smoothly to frame selected entity
    const target = obj.userData.cameraTarget ? obj.userData.cameraTarget.clone() : worldPos.clone().add(new THREE.Vector3(0, 3, 0));
    const pos = obj.userData.cameraPos ? obj.userData.cameraPos.clone() : worldPos.clone().add(new THREE.Vector3(16, 18, 22));

    this.glideCamera(pos, target);

    // Emit onSelect callback for UI panel
    this.onSelect({
      id: obj.userData.id,
      name: obj.userData.name,
      type: obj.userData.type,
      details: obj.userData.details || '',
      position: worldPos,
    });
  }

  deselect() {
    this.selectedEntity = null;
    this.followedEntity = null;
    this.selectionRing.visible = false;
    this.onSelect(null);
  }

  flyToArea(name) {
    this.cancelCinematic();
    const areas = {
      'Lobby': {
        target: new THREE.Vector3(0, 2, 2),
        pos: new THREE.Vector3(14, 18, 18),
      },
      'Vault Hall': {
        target: new THREE.Vector3(0, 5, -28),
        pos: new THREE.Vector3(18, 24, -8),
      },
      'Server Room': {
        target: new THREE.Vector3(13, 3, -8),
        pos: new THREE.Vector3(26, 18, 6),
      },
      'Shredder & Garage': {
        target: new THREE.Vector3(32, 4, -26),
        pos: new THREE.Vector3(46, 22, -8),
      },
      'Casino Tower': {
        target: new THREE.Vector3(-36, 18, 14),
        pos: new THREE.Vector3(-14, 28, 42),
      },
    };

    const dest = areas[name];
    if (dest) {
      this.glideCamera(dest.pos, dest.target);
    }
  }

  glideCamera(endPos, endTarget, durationSec = 1.2) {
    this.isTransitioning = true;
    this.transitionStartPos.copy(this.camera.position);
    this.transitionEndPos.copy(endPos);
    this.transitionStartTarget.copy(this.target);
    this.transitionEndTarget.copy(endTarget);
    this.transitionProgress = 0;
    this.transitionDuration = durationSec;
  }

  setCinematic(bool) {
    this.cinematic = Boolean(bool);
    if (this.cinematic) {
      this.cinematicTime = 0;
      this.followedEntity = null;
    }
  }

  cancelCinematic() {
    if (this.cinematic) {
      this.cinematic = false;
    }
  }

  update(delta) {
    // 1. Follow tracked moving character or vehicle
    if (this.followedEntity) {
      const worldPos = new THREE.Vector3();
      this.followedEntity.getWorldPosition(worldPos);
      this.target.lerp(worldPos.clone().add(new THREE.Vector3(0, 2, 0)), delta * 4);
      this.selectionRing.position.set(worldPos.x, 0.15, worldPos.z);
    }

    // 2. Camera transition glide
    if (this.isTransitioning) {
      this.transitionProgress += delta / this.transitionDuration;
      if (this.transitionProgress >= 1.0) {
        this.transitionProgress = 1.0;
        this.isTransitioning = false;
        this.camera.position.copy(this.transitionEndPos);
        this.target.copy(this.transitionEndTarget);
        this.spherical.setFromVector3(this.camera.position.clone().sub(this.target));
      } else {
        // Smooth cubic ease-in-out
        const t = this.transitionProgress;
        const ease = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

        this.camera.position.lerpVectors(this.transitionStartPos, this.transitionEndPos, ease);
        this.target.lerpVectors(this.transitionStartTarget, this.transitionEndTarget, ease);
        this.camera.lookAt(this.target);
        return;
      }
    }

    // 3. Cinematic Tour Glide Mode
    if (this.cinematic) {
      this.cinematicTime += delta * 0.12; // Complete tour in ~50 seconds
      const numPoints = this.cinematicWaypoints.length;
      const index = Math.floor(this.cinematicTime) % numPoints;
      const nextIndex = (index + 1) % numPoints;
      const frac = this.cinematicTime % 1.0;

      // Smooth cosine interpolation
      const smoothFrac = 0.5 - 0.5 * Math.cos(frac * Math.PI);

      const p1 = this.cinematicWaypoints[index];
      const p2 = this.cinematicWaypoints[nextIndex];

      const curTarget = new THREE.Vector3().lerpVectors(p1.target, p2.target, smoothFrac);
      const curOffset = new THREE.Vector3().lerpVectors(p1.offset, p2.offset, smoothFrac);

      this.target.lerp(curTarget, delta * 3);
      this.camera.position.lerp(curTarget.clone().add(curOffset), delta * 3);
      this.camera.lookAt(this.target);
      return;
    }

    // 4. Standard Orbit Position Update
    if (!this.isTransitioning) {
      const offset = new THREE.Vector3().setFromSpherical(this.spherical);
      this.camera.position.copy(this.target).add(offset);
      this.camera.lookAt(this.target);
    }
  }
}
