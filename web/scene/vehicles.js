/**
 * HeistBox 3D Scene - Vehicles & Aerial Units
 * - Armored Bank Transit Van (receives loot, getaway drive)
 * - Police Helicopter (patrol flight, spinning rotors, downward searchlight spotlight)
 * - Police Squad Cars (converge on Wanted Stars = 5 chase finale)
 */

import * as THREE from './three.module.js';

export class ArmoredVan {
  constructor(scene) {
    this.scene = scene;
    this.mesh = this.buildMesh();
    this.mesh.position.set(-26, 0, -14); // Parked near loading dock / garage alley
    this.mesh.rotation.y = Math.PI / 2;

    this.mesh.userData = {
      isEntity: true,
      id: 'van',
      name: 'Armored Getaway Van',
      type: 'vehicle',
      details: 'Reinforced ballistic transport truck with heavy vault cargo bay.',
    };

    this.rearDoorsOpen = false;
    scene.add(this.mesh);
  }

  buildMesh() {
    const group = new THREE.Group();

    // Body chassis (Heavy dark clay slate)
    const bodyMat = new THREE.MeshStandardMaterial({ color: 0x1E293B, roughness: 0.6, metalness: 0.3 });
    const trimMat = new THREE.MeshStandardMaterial({ color: 0xFFC93C, roughness: 0.4, metalness: 0.5 });
    const glassMat = new THREE.MeshStandardMaterial({ color: 0x38BDF8, roughness: 0.2, metalness: 0.8 });
    const wheelMat = new THREE.MeshStandardMaterial({ color: 0x0F172A, roughness: 0.9, metalness: 0.1 });

    // Main cab + cargo box
    const cab = new THREE.Mesh(new THREE.BoxGeometry(3.6, 2.4, 7.2), bodyMat);
    cab.position.y = 1.6;
    cab.castShadow = true;
    cab.receiveShadow = true;
    group.add(cab);

    // Gold signature security stripe
    const stripe = new THREE.Mesh(new THREE.BoxGeometry(3.64, 0.45, 7.24), trimMat);
    stripe.position.y = 1.6;
    group.add(stripe);

    // Armored Windshield
    const windshield = new THREE.Mesh(new THREE.BoxGeometry(3.0, 1.1, 0.2), glassMat);
    windshield.rotation.x = -Math.PI / 8;
    windshield.position.set(0, 2.1, 3.55);
    group.add(windshield);

    // Front Bumper & Grille
    const bumper = new THREE.Mesh(new THREE.BoxGeometry(3.8, 0.8, 0.6), trimMat);
    bumper.position.set(0, 0.8, 3.8);
    bumper.castShadow = true;
    group.add(bumper);

    // Headlights
    [-1.2, 1.2].forEach((x) => {
      const hl = new THREE.Mesh(new THREE.SphereGeometry(0.25, 8, 8), new THREE.MeshBasicMaterial({ color: 0xFFFBEB }));
      hl.position.set(x, 1.2, 3.9);
      group.add(hl);
    });

    // 4 Heavy-duty Wheels
    this.wheels = [];
    const wheelGeo = new THREE.CylinderGeometry(0.7, 0.7, 0.6, 12);
    [[-1.8, 0.7, 2.2], [1.8, 0.7, 2.2], [-1.8, 0.7, -2.2], [1.8, 0.7, -2.2]].forEach(([wx, wy, wz]) => {
      const wheel = new THREE.Mesh(wheelGeo, wheelMat);
      wheel.rotation.z = Math.PI / 2;
      wheel.position.set(wx, wy, wz);
      wheel.castShadow = true;
      group.add(wheel);
      this.wheels.push(wheel);
    });

    // Rear cargo doors (Pivots open to receive coins)
    this.rearLeftDoor = new THREE.Group();
    this.rearLeftDoor.position.set(-1.6, 1.6, -3.6);
    const doorL = new THREE.Mesh(new THREE.BoxGeometry(1.6, 2.2, 0.15), bodyMat);
    doorL.position.x = 0.8;
    this.rearLeftDoor.add(doorL);
    group.add(this.rearLeftDoor);

    this.rearRightDoor = new THREE.Group();
    this.rearRightDoor.position.set(1.6, 1.6, -3.6);
    const doorR = new THREE.Mesh(new THREE.BoxGeometry(1.6, 2.2, 0.15), bodyMat);
    doorR.position.x = -0.8;
    this.rearRightDoor.add(doorR);
    group.add(this.rearRightDoor);

    return group;
  }

  openDoors() {
    this.rearDoorsOpen = true;
  }

  closeDoors() {
    this.rearDoorsOpen = false;
  }

  update(delta) {
    const targetAngle = this.rearDoorsOpen ? Math.PI / 2.2 : 0;
    this.rearLeftDoor.rotation.y = THREE.MathUtils.lerp(this.rearLeftDoor.rotation.y, -targetAngle, delta * 6);
    this.rearRightDoor.rotation.y = THREE.MathUtils.lerp(this.rearRightDoor.rotation.y, targetAngle, delta * 6);
  }
}

export class PoliceHelicopter {
  constructor(scene) {
    this.scene = scene;
    this.mesh = this.buildMesh();
    this.mesh.position.set(34, 11, 18); // Starts on police helipad
    this.targetPosition = new THREE.Vector3(34, 11, 18);
    this.state = 'landed'; // 'landed', 'patrolling', 'tracking'
    this.spotlightTarget = new THREE.Object3D();
    scene.add(this.spotlightTarget);

    this.mesh.userData = {
      isEntity: true,
      id: 'helicopter',
      name: 'Police Patrol Chopper',
      type: 'aircraft',
      details: 'Airborne surveillance helicopter with steerable high-intensity searchlight.',
    };

    scene.add(this.mesh);
  }

  buildMesh() {
    const group = new THREE.Group();

    const bodyMat = new THREE.MeshStandardMaterial({ color: 0x1E3A8A, roughness: 0.5, metalness: 0.4 });
    const whiteMat = new THREE.MeshStandardMaterial({ color: 0xF8FAFC, roughness: 0.6 });
    const glassMat = new THREE.MeshStandardMaterial({ color: 0x38BDF8, roughness: 0.2, metalness: 0.8, transparent: true, opacity: 0.8 });
    const metalMat = new THREE.MeshStandardMaterial({ color: 0x1E293B, roughness: 0.4, metalness: 0.8 });

    // Fuselage (Cockpit & cabin)
    const body = new THREE.Mesh(new THREE.BoxGeometry(2.4, 2.2, 5.0), bodyMat);
    body.position.y = 1.4;
    body.castShadow = true;
    group.add(body);

    // White Police belly stripe
    const belly = new THREE.Mesh(new THREE.BoxGeometry(2.44, 0.4, 5.04), whiteMat);
    belly.position.y = 1.0;
    group.add(belly);

    // Curved cockpit bubble glass
    const glass = new THREE.Mesh(new THREE.ConeGeometry(1.6, 2.2, 4), glassMat);
    glass.rotation.x = -Math.PI / 2;
    glass.position.set(0, 1.4, 2.6);
    group.add(glass);

    // Tail boom
    const tailBoom = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.6, 6.0, 6), bodyMat);
    tailBoom.rotation.x = Math.PI / 2;
    tailBoom.position.set(0, 1.8, -4.8);
    tailBoom.castShadow = true;
    group.add(tailBoom);

    // Tail fin
    const fin = new THREE.Mesh(new THREE.BoxGeometry(0.15, 1.8, 1.2), whiteMat);
    fin.position.set(0, 2.4, -7.5);
    group.add(fin);

    // Landing skids
    const skidGeo = new THREE.BoxGeometry(0.15, 0.15, 4.8);
    const skidL = new THREE.Mesh(skidGeo, metalMat);
    skidL.position.set(-1.3, 0.1, 0.2);
    group.add(skidL);

    const skidR = new THREE.Mesh(skidGeo, metalMat);
    skidR.position.set(1.3, 0.1, 0.2);
    group.add(skidR);

    // Skid struts
    [[-1.3, 1.2], [-1.3, -1.0], [1.3, 1.2], [1.3, -1.0]].forEach(([sx, sz]) => {
      const strut = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 0.8, 6), metalMat);
      strut.position.set(sx * 0.75, 0.5, sz);
      strut.rotation.z = sx > 0 ? -0.3 : 0.3;
      group.add(strut);
    });

    // Main Rotor Mast & Twin Rotor Blades
    const rotorMast = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 0.8, 6), metalMat);
    rotorMast.position.set(0, 2.7, 0.2);
    group.add(rotorMast);

    this.mainRotor = new THREE.Group();
    this.mainRotor.position.set(0, 3.1, 0.2);

    const bladeGeo = new THREE.BoxGeometry(9.6, 0.06, 0.45);
    const blade1 = new THREE.Mesh(bladeGeo, metalMat);
    const blade2 = new THREE.Mesh(bladeGeo, metalMat);
    blade2.rotation.y = Math.PI / 2;

    this.mainRotor.add(blade1);
    this.mainRotor.add(blade2);
    group.add(this.mainRotor);

    // Tail Rotor
    this.tailRotor = new THREE.Mesh(new THREE.BoxGeometry(0.05, 1.8, 0.25), metalMat);
    this.tailRotor.position.set(0.2, 2.4, -7.6);
    group.add(this.tailRotor);

    // DOWNWARD SEARCHLIGHT SPOTLIGHT
    this.searchlight = new THREE.SpotLight(0xFFFBEB, 3.5, 60, Math.PI / 6, 0.4, 1.5);
    this.searchlight.position.set(0, 0.4, 1.5);
    this.searchlight.castShadow = true;
    this.searchlight.shadow.mapSize.width = 512;
    this.searchlight.shadow.mapSize.height = 512;
    group.add(this.searchlight);

    // Searchlight visual cone beam
    const coneGeo = new THREE.ConeGeometry(3.5, 14, 12, 1, true);
    const coneMat = new THREE.MeshBasicMaterial({
      color: 0xFEF08A,
      transparent: true,
      opacity: 0.18,
      side: THREE.DoubleSide,
    });
    this.searchBeam = new THREE.Mesh(coneGeo, coneMat);
    this.searchBeam.position.set(0, -7.0, 1.5);
    group.add(this.searchBeam);

    return group;
  }

  takeoff() {
    this.state = 'patrolling';
  }

  trackTarget(pos) {
    this.state = 'tracking';
    this.targetPosition.set(pos.x, 18, pos.z);
    this.spotlightTarget.position.copy(pos);
    this.searchlight.target = this.spotlightTarget;
  }

  update(delta, time, thiefPos) {
    // Spin rotor blades
    this.mainRotor.rotation.y += delta * 24;
    this.tailRotor.rotation.x += delta * 30;

    if (this.state === 'patrolling') {
      // Circle the bank campus smoothly
      const radius = 32;
      const angle = time * 0.4;
      const targetX = Math.cos(angle) * radius;
      const targetZ = Math.sin(angle) * radius - 6;
      const targetY = 18 + Math.sin(time * 1.5) * 1.2;

      this.mesh.position.lerp(new THREE.Vector3(targetX, targetY, targetZ), delta * 1.8);

      // Look in direction of flight with banking tilt
      const tangent = new THREE.Vector3(-Math.sin(angle), 0, Math.cos(angle)).normalize();
      this.mesh.quaternion.slerp(
        new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), tangent),
        delta * 3
      );
      this.mesh.rotation.z = -0.2; // Bank into turn

      // Searchlight scans campus ground
      this.spotlightTarget.position.set(targetX * 0.5, 0, targetZ * 0.5);
      this.searchlight.target = this.spotlightTarget;
    } else if (this.state === 'tracking' && thiefPos) {
      // Aggressive chase positioning: hover above thief with searchlight pinned
      const hoverX = thiefPos.x + Math.sin(time * 0.8) * 4;
      const hoverZ = thiefPos.z + Math.cos(time * 0.8) * 4 + 4;
      const hoverY = 16 + Math.sin(time * 2) * 0.6;

      this.mesh.position.lerp(new THREE.Vector3(hoverX, hoverY, hoverZ), delta * 2.8);

      this.spotlightTarget.position.copy(thiefPos);
      this.searchlight.target = this.spotlightTarget;

      // Face towards thief
      const toThief = thiefPos.clone().sub(this.mesh.position);
      toThief.y = 0;
      toThief.normalize();
      this.mesh.quaternion.slerp(
        new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), toThief),
        delta * 4
      );
    }
  }
}

export class PoliceSquadCars {
  constructor(scene) {
    this.scene = scene;
    this.cars = [];
    this.active = false;

    // Spawn 2 squad cars initially at Police Station bays
    this.car1 = this.createPoliceCar(new THREE.Vector3(30, 0, 26), 0);
    this.car2 = this.createPoliceCar(new THREE.Vector3(40, 0, 26), 0);

    scene.add(this.car1.mesh);
    scene.add(this.car2.mesh);
    this.cars.push(this.car1, this.car2);
  }

  createPoliceCar(pos, rotY) {
    const group = new THREE.Group();
    const bodyMat = new THREE.MeshStandardMaterial({ color: 0x1E3A8A, roughness: 0.5 });
    const whiteMat = new THREE.MeshStandardMaterial({ color: 0xF8FAFC, roughness: 0.5 });
    const wheelMat = new THREE.MeshStandardMaterial({ color: 0x0F172A, roughness: 0.9 });

    // Chassis
    const chassis = new THREE.Mesh(new THREE.BoxGeometry(2.4, 1.2, 5.0), bodyMat);
    chassis.position.y = 0.9;
    chassis.castShadow = true;
    group.add(chassis);

    // White door panel
    const doorPanel = new THREE.Mesh(new THREE.BoxGeometry(2.44, 0.9, 2.2), whiteMat);
    doorPanel.position.y = 0.9;
    group.add(doorPanel);

    // Cab / Roof
    const roof = new THREE.Mesh(new THREE.BoxGeometry(2.0, 1.0, 2.6), bodyMat);
    roof.position.set(0, 1.8, -0.2);
    roof.castShadow = true;
    group.add(roof);

    // Siren Lightbar (Red and Blue)
    const sirenBar = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.25, 0.4), new THREE.MeshStandardMaterial({ color: 0x0F172A }));
    sirenBar.position.set(0, 2.45, -0.2);
    group.add(sirenBar);

    const redLight = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.2, 0.35), new THREE.MeshBasicMaterial({ color: 0xEF4444 }));
    redLight.position.set(-0.4, 2.5, -0.2);
    group.add(redLight);

    const blueLight = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.2, 0.35), new THREE.MeshBasicMaterial({ color: 0x38BDF8 }));
    blueLight.position.set(0.4, 2.5, -0.2);
    group.add(blueLight);

    // Wheels
    const wheelGeo = new THREE.CylinderGeometry(0.5, 0.5, 0.4, 10);
    [[-1.2, 0.5, 1.6], [1.2, 0.5, 1.6], [-1.2, 0.5, -1.6], [1.2, 0.5, -1.6]].forEach(([wx, wy, wz]) => {
      const w = new THREE.Mesh(wheelGeo, wheelMat);
      w.rotation.z = Math.PI / 2;
      w.position.set(wx, wy, wz);
      group.add(w);
    });

    group.position.copy(pos);
    group.rotation.y = rotY;

    return {
      mesh: group,
      redLight,
      blueLight,
      target: null,
      speed: 12.0,
      active: false,
    };
  }

  convergeOnTarget(targetPos) {
    this.active = true;
    this.car1.target = targetPos.clone().add(new THREE.Vector3(-4, 0, 3));
    this.car2.target = targetPos.clone().add(new THREE.Vector3(4, 0, 3));
    this.car1.active = true;
    this.car2.active = true;
  }

  reset() {
    this.active = false;
    this.car1.mesh.position.set(30, 0, 26);
    this.car1.mesh.rotation.y = 0;
    this.car2.mesh.position.set(40, 0, 26);
    this.car2.mesh.rotation.y = 0;
    this.car1.active = false;
    this.car2.active = false;
  }

  update(delta, time) {
    this.cars.forEach((car) => {
      if (car.active && car.target) {
        // Flash sirens alternately
        const flash = Math.sin(time * 18) > 0;
        car.redLight.visible = flash;
        car.blueLight.visible = !flash;

        // Drive towards convergence point
        const toTarget = car.target.clone().sub(car.mesh.position);
        toTarget.y = 0;
        const dist = toTarget.length();

        if (dist > 0.4) {
          toTarget.normalize();
          car.mesh.position.addScaledVector(toTarget, car.speed * delta);

          const targetAngle = Math.atan2(toTarget.x, toTarget.z);
          car.mesh.rotation.y = THREE.MathUtils.lerp(car.mesh.rotation.y, targetAngle, delta * 8);
        }
      }
    });
  }
}
