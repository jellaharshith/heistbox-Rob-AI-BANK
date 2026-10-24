/**
 * HeistBox 3D Scene - Simulation Engine
 * Drives the 6-step heist progression, vault verdicts, wanted stars, and police-chase finale.
 */

import * as audio from './audio.js';

export class SimulationEngine {
  constructor(worldManager, characterManager, vaultManager, vehicleManager, effectsManager, controls) {
    this.world = worldManager;
    this.chars = characterManager;
    this.vaults = vaultManager;
    this.vehicles = vehicleManager;
    this.effects = effectsManager;
    this.controls = controls;

    this.currentStep = 0;
    this.wantedStars = 0;
    this.isPlaying = false;
    this.stepTimeout = null;
    this.onStateChange = () => {};
  }

  setStep(step) {
    this.currentStep = step;
    if (this.onStateChange) {
      this.onStateChange({ step: this.currentStep, stars: this.wantedStars });
    }

    switch (step) {
      case 1:
        this.runStep1();
        break;
      case 2:
        this.runStep2();
        break;
      case 3:
        this.runStep3();
        break;
      case 4:
        this.runStep4();
        break;
      case 5:
        this.runStep5();
        break;
      case 6:
        this.runStep6();
        break;
      default:
        this.reset();
        break;
    }
  }

  setWantedStars(stars) {
    this.wantedStars = Math.max(0, Math.min(5, stars));
    if (this.onStateChange) {
      this.onStateChange({ step: this.currentStep, stars: this.wantedStars });
    }

    if (this.wantedStars >= 3) {
      this.vehicles.helicopter.takeoff();
    }

    if (this.wantedStars === 5) {
      this.triggerPoliceChaseFinale();
    }
  }

  /** Step 1: Thief approaches counter and bluffs */
  runStep1() {
    const thief = this.chars.thief;
    if (!thief) return;

    // Walk to Counter Queue Slot 1
    thief.setDestination(0, 4.5, () => {
      thief.state = 'talking';
      thief.showEmote('💬', 4000);
      this.world.updateTickerText('🚨 PROMPT INJECTION DETECTED: "$4,975 GRANDMA WIRE EXPLOIT"  •  ');
    });
  }

  /** Step 2: Teller creates request, routes to all 3 vaults */
  runStep2() {
    const teller = this.chars.teller;
    if (teller) {
      teller.state = 'talking';
      teller.showEmote('❓', 3000);
    }

    // Launch routing packets across the floor to all 3 vaults
    this.vaults.triggerRoutingLaser();
    this.world.updateTickerText('⚡ MULTI-GATE ROUTING INITIATED: EVALUATING 3 VAULT PROVERS SIMULTANEOUSLY  •  ');
  }

  /** Step 3: LEFT Vault "LLM Judge" Robbed */
  runStep3() {
    this.vaults.triggerLeftRobbery(() => {
      this.chars.thief.showEmote('💰', 3000);
      this.world.updateTickerText('⚠️ LEFT VAULT (LLM JUDGE) EXPLOITED: $4,975.00 WIRED NAIVELY  •  ');
    });
  }

  /** Step 4: MIDDLE Vault "Kill-Switch" Panic Lockdown */
  runStep4() {
    this.vaults.triggerMiddleLockdown(() => {
      if (this.chars.teller) {
        this.chars.teller.showEmote('🚨', 3500);
      }
      this.world.updateTickerText('🧊 MIDDLE VAULT (KILL-SWITCH) LOCKDOWN: HONEST $25 REFUND FROZEN & DENIED  •  ');
    });
  }

  /** Step 5: RIGHT Vault "PAIR Gate" Surgical Defusal */
  runStep5() {
    this.vaults.triggerRightPAIRDefusal(
      (intensity) => this.effects.shakeCamera(intensity),
      () => {
        this.chars.thief.showEmote('⚡', 3000);
        this.world.updateTickerText('🛡️ RIGHT VAULT (PAIR GATE) DEFUSED IN 1.4ms: $4,975 SHREDDED • $25 SENT TO FACE ID  •  ');
      }
    );
  }

  /** Step 6: Getaway & Police Alert */
  runStep6() {
    this.setWantedStars(5);
  }

  /** Police-Chase Finale at Wanted Stars = 5 */
  triggerPoliceChaseFinale() {
    audio.startPoliceSiren(5.5);

    // 1. Helicopter swoops down and pins searchlight on thief
    this.vehicles.helicopter.trackTarget(this.chars.thief.mesh.position);

    // 2. Squad cars converge with flashing lights
    this.vehicles.policeCars.convergeOnTarget(this.chars.thief.mesh.position);

    // 3. Thief panics
    this.chars.thief.showEmote('🚨', 4000);
    this.chars.thief.setDestination(0, 16); // Runs back to plaza

    // 4. BUSTED Stamp slams onto screen
    setTimeout(() => {
      this.effects.showBustedStamp(3200);
      this.world.updateTickerText('⚖️ BUSTED! 100% OF VAULT PROTECTED • ZERO DATABASE LOSS  •  ');
    }, 1800);

    // 5. Reset after finale completes
    setTimeout(() => {
      if (this.isPlaying) {
        this.reset();
        this.playLoop();
      }
    }, 6500);
  }

  playLoop() {
    this.isPlaying = true;
    this.reset();

    const sequence = [
      { step: 1, delay: 1000 },
      { step: 2, delay: 4200 },
      { step: 3, delay: 4000 },
      { step: 4, delay: 4500 },
      { step: 5, delay: 4500 },
      { step: 6, delay: 5000 },
    ];

    let currentIdx = 0;
    const runNext = () => {
      if (!this.isPlaying) return;
      if (currentIdx < sequence.length) {
        const item = sequence[currentIdx];
        this.setStep(item.step);
        currentIdx++;
        this.stepTimeout = setTimeout(runNext, item.delay);
      }
    };
    runNext();
  }

  stopLoop() {
    this.isPlaying = false;
    if (this.stepTimeout) {
      clearTimeout(this.stepTimeout);
      this.stepTimeout = null;
    }
  }

  reset() {
    this.stopLoop();
    this.currentStep = 0;
    this.wantedStars = 0;

    this.vaults.reset();
    this.vehicles.policeCars.reset();
    this.vehicles.helicopter.state = 'landed';
    this.vehicles.helicopter.mesh.position.set(34, 11, 18);
    if (this.effects.bustedSprite) {
      this.effects.bustedSprite.visible = false;
    }

    // Reset characters
    if (this.chars.thief) {
      this.chars.thief.mesh.position.set(0, 0, 36);
      this.chars.thief.position.set(0, 0, 36);
      this.chars.thief.state = 'idle';
      this.chars.thief.bubbleMesh.visible = false;
    }

    if (this.onStateChange) {
      this.onStateChange({ step: 0, stars: 0 });
    }

    this.world.updateTickerText('🎰 JACKPOT: $5,000,000.00  •  ⚡ PAIR KERNEL 1.4ms GATE  •  🚨 HEISTGUARD ACTIVE  •  ');
  }
}
