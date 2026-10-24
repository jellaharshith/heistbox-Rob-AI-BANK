/**
 * HeistBox 3D Scene - Main Export Module
 * Exports: mountScene(canvas, store)
 * Reacts to live contracts / mock-server.js events via WebSocket or store.
 */

import * as THREE from './three.module.js';
import * as audio from './audio.js';
import { WorldManager } from './world.js';
import { CharacterManager } from './characters.js';
import { ArmoredVan, PoliceHelicopter, PoliceSquadCars } from './vehicles.js';
import { VaultManager } from './vaults.js';
import { EffectsManager } from './effects.js';
import { SceneControls } from './controls.js';
import { SimulationEngine } from './simulation.js';

export { audio };

/**
 * Mounts the 3D isometric Vegas-style bank campus onto the given canvas element.
 * @param {HTMLCanvasElement} canvas - Target canvas element
 * @param {Object} [store] - Optional contract event emitter or state store
 * @returns {Object} Public API controls for the scene
 */
export function mountScene(canvas, store = null) {
  if (!canvas) {
    throw new Error('mountScene requires a valid HTMLCanvasElement.');
  }

  // 1. Scene, Camera, Renderer Setup
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0B0F1E);

  const width = canvas.clientWidth || window.innerWidth || 800;
  const height = canvas.clientHeight || window.innerHeight || 600;

  const camera = new THREE.PerspectiveCamera(38, width / height, 1, 400);
  camera.position.set(45, 52, 65); // Classic isometric perspective
  camera.lookAt(0, 4, 0);

  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    powerPreference: 'high-performance',
    alpha: false,
  });
  renderer.setSize(width, height, false);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;

  // 2. Subsystem Managers
  const world = new WorldManager(scene);
  const chars = new CharacterManager(scene, world);
  const van = new ArmoredVan(scene);
  const helicopter = new PoliceHelicopter(scene);
  const policeCars = new PoliceSquadCars(scene);
  const vaults = new VaultManager(scene, world, van);
  const effects = new EffectsManager(scene, renderer, camera);

  // Vehicles coordinator object
  const vehicles = {
    van,
    helicopter,
    policeCars,
    update: (delta, time) => {
      van.update(delta);
      helicopter.update(delta, time, chars.thief ? chars.thief.mesh.position : null);
      policeCars.update(delta, time);
    },
  };

  // 3. User Controls & Interaction
  let selectCallback = null;
  const controls = new SceneControls(camera, canvas, scene, world, (entity) => {
    if (selectCallback) selectCallback(entity);
  });

  // 4. Simulation Engine
  const simulation = new SimulationEngine(world, chars, vaults, vehicles, effects, controls);

  // 5. Connect to Store or Mock-Server WebSocket
  function handleVaultVerdict(v) {
    if (!v) return;
    const vName = v.vault || (v.left_vault_llm_judge ? 'left' : v.center_firewall ? 'middle' : 'right');
    if (vName === 'left') {
      vaults.triggerLeftRobbery();
    } else if (vName === 'middle') {
      vaults.triggerMiddleLockdown();
    } else if (vName === 'right') {
      vaults.triggerRightPAIRDefusal((intensity) => effects.shakeCamera(intensity));
    }
  }

  function handleWeather(w) {
    if (!w) return;
    const cond = typeof w === 'string' ? w : (w.condition || w.label || 'Clear Night');
    const mapping = {
      'clear_night': 'Clear Night',
      'rain': 'Rain',
      'fog': 'Fog',
      'dust': 'Sandstorm',
      'sandstorm': 'Sandstorm',
      'Clear Night': 'Clear Night',
      'Rain': 'Rain',
      'Fog': 'Fog',
      'Sandstorm': 'Sandstorm',
      'Dust': 'Sandstorm',
    };
    effects.setWeather(mapping[cond] || 'Clear Night');
  }

  function handleAgentAction(action) {
    if (!action) return;
    const agent = chars.getAgent(action.agent_id);
    if (agent) {
      if (action.say) {
        agent.showEmote(action.say, 4000);
      } else if (action.thought) {
        agent.showEmote(action.thought, 3000);
      } else if (action.tool) {
        agent.showEmote('⚡', 2500);
      }
    }
  }

  function handleHeistStep(s) {
    if (!s) return;
    const stepNum = typeof s === 'number' ? s : s.step;
    simulation.setStep(stepNum);

    if (s.detail) {
      world.updateTickerText(`⚡ ${s.name || 'HEIST'}: ${s.detail.toUpperCase()}  •  `);
    }
  }

  // A) If custom store is passed
  if (store) {
    if (typeof store.subscribe === 'function') {
      let prevState = {};
      store.subscribe((state) => {
        if (!state) return;
        if (state.heist_step !== undefined && state.heist_step !== prevState.heist_step) {
          handleHeistStep(state.heist_step);
        }
        if (state.wanted_stars !== undefined && state.wanted_stars !== prevState.wanted_stars) {
          simulation.setWantedStars(state.wanted_stars);
        }
        if (state.weather && state.weather !== prevState.weather) {
          handleWeather(state.weather);
        }
        if (state.time_of_day !== undefined && state.time_of_day !== prevState.time_of_day) {
          effects.setTimeOfDay(state.time_of_day);
        }
        if (state.vault_verdict) {
          handleVaultVerdict(state.vault_verdict);
        }
        if (state.agent_action) {
          handleAgentAction(state.agent_action);
        }
        prevState = { ...state };
      });
    }

    if (typeof store.on === 'function') {
      store.on('heist_step', handleHeistStep);
      store.on('wanted_stars', (st) => simulation.setWantedStars(typeof st === 'number' ? st : st.stars));
      store.on('weather', handleWeather);
      store.on('time_of_day', (t) => effects.setTimeOfDay(t));
      store.on('vault_verdict', handleVaultVerdict);
      store.on('agent_action', handleAgentAction);
      store.on('ticker', (tk) => tk.message && world.updateTickerText(tk.message + '  •  '));
    }
  } else {
    // B) Standalone mode: Try connecting to mock-server.js or real server WebSocket
    let ws = null;
    const connectWS = (port) => {
      try {
        const socket = new WebSocket(`ws://${window.location.hostname || 'localhost'}:${port}/ws`);
        socket.onopen = () => {
          console.log(`[HeistBox 3D] Connected to live contract events on port ${port}`);
          const badge = document.getElementById('badge-sim');
          if (badge) {
            badge.innerHTML = `<div class="pulse-dot" style="background:#38BDF8;box-shadow:0 0 10px #38BDF8;"></div><span>LIVE CONTRACTS (:${port})</span>`;
            badge.style.color = '#38BDF8';
            badge.style.borderColor = 'rgba(56, 189, 248, 0.45)';
          }
        };
        socket.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (!msg || !msg.type) return;

            switch (msg.type) {
              case 'heist_step':
                handleHeistStep(msg.data);
                break;
              case 'vault_verdict':
                handleVaultVerdict(msg.data);
                break;
              case 'wanted_stars':
                simulation.setWantedStars(msg.data.stars);
                break;
              case 'weather':
                handleWeather(msg.data);
                break;
              case 'ticker':
                if (msg.data && msg.data.message) {
                  world.updateTickerText(msg.data.message + '  •  ');
                }
                break;
              case 'agent_action':
                handleAgentAction(msg.data);
                break;
            }
          } catch {}
        };
        socket.onerror = () => {
          // If 8788 fails and we haven't tried 8787, try 8787
          if (port === 8788) connectWS(8787);
        };
        ws = socket;
      } catch {}
    };

    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      const isForcedSim = urlParams.has('sim') || urlParams.has('standalone');
      if (!isForcedSim) {
        connectWS(8788);
      } else {
        console.log('[HeistBox 3D] Running in pure standalone SIMULATION mode');
      }
    }
  }

  // 6. Handle Resize
  let resizeObserver = null;
  const onResize = () => {
    const w = canvas.clientWidth || window.innerWidth;
    const h = canvas.clientHeight || window.innerHeight;
    const aspect = w / h;
    camera.aspect = aspect;
    if (aspect < 1.0) {
      // Mobile portrait: widen vertical FOV proportionally so campus fits nicely
      camera.fov = Math.min(68, 38 / Math.max(0.48, aspect));
    } else {
      camera.fov = 38;
    }
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
  };

  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(onResize);
    resizeObserver.observe(canvas.parentElement || canvas);
  } else {
    window.addEventListener('resize', onResize);
  }

  // 7. Animation Loop
  let isRunning = true;
  let animationFrameId = null;
  const clock = new THREE.Clock();

  function animate() {
    if (!isRunning) return;
    animationFrameId = requestAnimationFrame(animate);

    const delta = Math.min(clock.getDelta(), 0.1);
    const time = clock.getElapsedTime();

    // Update subsystems
    world.update(delta, time);
    chars.update(delta, time);
    vehicles.update(delta, time);
    vaults.update(delta, time);
    effects.update(delta);
    controls.update(delta);

    renderer.render(scene, camera);
  }

  animate();

  // 8. Public API Controls
  return {
    scene,
    camera,
    renderer,
    controls,
    world,
    chars,
    vaults,
    vehicles,
    effects,
    simulation,
    audio,
    flyToArea: (name) => controls.flyToArea(name),
    setWeather: (mode) => effects.setWeather(mode),
    setTimeOfDay: (t) => effects.setTimeOfDay(t),
    setCinematic: (bool) => controls.setCinematic(bool),
    setMuted: (bool) => audio.setMuted(bool),
    toggleMute: () => audio.toggleMute(),
    selectEntity: (obj) => controls.selectEntity(obj),
    onSelect: (cb) => {
      selectCallback = cb;
    },
    setStep: (s) => simulation.setStep(s),
    setWantedStars: (s) => simulation.setWantedStars(s),
    playLoop: () => simulation.playLoop(),
    stopLoop: () => simulation.stopLoop(),
    reset: () => simulation.reset(),
    setQuality: (isLow) => {
      renderer.shadowMap.enabled = !isLow;
      renderer.setPixelRatio(isLow ? 1.0 : Math.min(window.devicePixelRatio || 1, 2));
      scene.traverse((node) => {
        if (node.isMesh) {
          node.castShadow = !isLow;
          node.receiveShadow = !isLow;
        }
      });
      console.log(`[HeistBox 3D] Quality set to ${isLow ? 'LOW' : 'HIGH'}. Draw calls:`, renderer.info.render.calls);
    },
    destroy: () => {
      isRunning = false;
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
      if (resizeObserver) resizeObserver.disconnect();
      window.removeEventListener('resize', onResize);
      renderer.dispose();
    },
    simulation,
    scene,
    camera,
    renderer,
  };
}
