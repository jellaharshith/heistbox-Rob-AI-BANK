import { useEffect, useMemo } from "react";
import { useAnimations } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { Color, Mesh, MeshStandardMaterial, Material, Vector3 } from "three";
import { useAsset, required, validateClips } from "./assets";
import { useClip } from "./animation";
import { useGame } from "../game/store";
import { Bills } from "./Bills";
import { Effects } from "./Effects";
export function Props() {
  const asset = useAsset("PROPS");
  const env = useAsset("ENV_Bank");
  const setup = useMemo(() => {
    const root = asset.scene.clone(true);
    const names = [
      "VAULT_L_Door",
      "VAULT_M_Door",
      "VAULT_R_Door",
      "PROP_Shredder",
      "FX_Laser",
      "PROP_CashSmall",
      "PROP_CashHeist",
      "PROP_Bill",
      "PROP_Megaphone",
      "PROP_WantedPoster",
      "PROP_Terminal",
      "PROP_Phone",
      "FX_LockdownStrip_L",
      "FX_LockdownStrip_M",
      "FX_LockdownStrip_R",
    ];
    names.forEach((n) => required(root, n));
    validateClips(asset, [
      "VAULT_L_Door_Ajar",
      ...["L", "M", "R"].flatMap((v) => [
        `VAULT_${v}_Door_Open`,
        `VAULT_${v}_Door_Slam`,
      ]),
    ]);
    const materials = new Map<MeshStandardMaterial, MeshStandardMaterial>();
    root.traverse((node) => {
      const o = node as Mesh;
      if (o.isMesh) {
        const copy = (source: Material) => {
          const m = source as MeshStandardMaterial;
          if (!materials.has(m)) materials.set(m, m.clone());
          return materials.get(m)!;
        };
        o.material = Array.isArray(o.material)
          ? o.material.map(copy)
          : copy(o.material);
      }
    });
    for (const name of [
      "MAT_ScreenRuntime",
      "MAT_PosterRuntime",
      "MAT_PhoneRuntime",
    ])
      if (![...materials.values()].some((m) => m.name === name)) {
        console.error(`[GLB CONTRACT] Missing material ${name}`);
        throw new Error(`Missing material ${name}`);
      }
    required(root, "PROP_Bill").visible = false;
    required(root, "PROP_Phone").visible = false; // Customer already carries the phone.
    required(root, "PROP_Terminal").position.set(0.9, 1.15, -0.05);
    required(root, "PROP_Megaphone").position.set(2.2, 1.22, -0.1);
    const posterObj = required(root, "PROP_WantedPoster");
    posterObj.position.set(-0.75, 1.22, 0.05);
    posterObj.rotation.set(-0.15, 0.1, 0);
    posterObj.scale.setScalar(1.2);
    const cash = required(root, "PROP_CashHeist");
    const dissolve = { value: 0 };
    const owned: MeshStandardMaterial[] = [];
    cash.traverse((node) => {
      const o = node as Mesh;
      if (o.isMesh) {
        const source = Array.isArray(o.material) ? o.material : [o.material];
        const copies = source.map((m) => {
          const mat = m.clone() as MeshStandardMaterial;
          owned.push(mat);
          mat.onBeforeCompile = (shader) => {
            shader.uniforms.uDissolve = dissolve;
            shader.vertexShader = "varying vec3 vCash;\n" + shader.vertexShader;
            shader.vertexShader = shader.vertexShader.replace(
              "#include <begin_vertex>",
              "#include <begin_vertex>\nvCash = position;",
            );
            shader.fragmentShader =
              "uniform float uDissolve;\nvarying vec3 vCash;\n" +
              shader.fragmentShader;
            shader.fragmentShader = shader.fragmentShader.replace(
              "#include <clipping_planes_fragment>",
              "#include <clipping_planes_fragment>\nfloat noise = fract(sin(dot(floor(vCash * 120.0), vec3(12.9898,78.233,45.164))) * 43758.5453); if (noise < uDissolve) discard;",
            );
          };
          mat.customProgramCacheKey = () => "heist-dissolve-v1";
          return mat;
        });
        o.material = Array.isArray(o.material) ? copies : copies[0];
      }
    });
    const middle = required(root, "VAULT_M_Door") as Mesh;
    const ice = middle.material as MeshStandardMaterial;
    const originalIce = ice.color.clone();
    const stripM = required(root, "FX_LockdownStrip_M") as Mesh;
    const stripR = required(root, "FX_LockdownStrip_R") as Mesh;
    const laser = required(root, "FX_Laser");
    const target = required(env.scene, "ANCHOR_LaserTarget").position.clone();
    const source = new Vector3(4.6, 2.65, -5.3),
      direction = target.clone().sub(source);
    laser.position.copy(source);
    laser.quaternion.setFromUnitVectors(
      new Vector3(-1, 0, 0),
      direction.clone().normalize(),
    );
    laser.scale.x = direction.length() / 1.64;
    return {
      root,
      cash,
      dissolve,
      materials: [...materials.values(), ...owned],
      ice,
      originalIce,
      selection: [stripM, stripR, laser],
      stripM: stripM.material as MeshStandardMaterial,
      stripR: stripR.material as MeshStandardMaterial,
      laser,
      target,
      small: required(root, "PROP_CashSmall"),
      poster: required(root, "PROP_WantedPoster"),
      color: new Color("#9fe7ff"),
    };
  }, [asset, env]);
  useEffect(() => () => setup.materials.forEach((m) => m.dispose()), [setup]);
  const { actions } = useAnimations(asset.animations, setup.root);
  useClip(
    actions,
    useGame((s) => s.clips.L),
  );
  useClip(
    actions,
    useGame((s) => s.clips.M),
  );
  useClip(
    actions,
    useGame((s) => s.clips.R),
  );
  useFrame(() => {
    const s = useGame.getState(),
      now = performance.now(),
      elapsed = (now - s.stageAt) / 1000;
    const frozen = s.revealed.includes("M");
    setup.ice.roughness = 0.18;
    setup.ice.metalness = 0.1;
    setup.ice.color.copy(setup.originalIce).lerp(new Color("#6fe2ff"), frozen ? 0.85 : 0);
    setup.stripM.emissive.set(frozen ? "#ff1a35" : "#000000");
    setup.stripM.emissiveIntensity = frozen
      ? 3.2 + Math.sin(now * 0.012) * 1.5
      : 0;
    setup.stripR.emissive.set("#00f5d4");
    setup.stripR.emissiveIntensity = s.revealed.includes("R")
      ? 3.0 + Math.sin(now * 0.014) * 1.0
      : 0.6;
    setup.laser.visible = s.stage === "fire";
    if (s.stage === "fire") {
      const pulse = 1 + Math.sin(now * 0.06) * 0.35;
      setup.laser.scale.y = pulse;
      setup.laser.scale.z = pulse;
    }
    const destroying = s.stage === "fire";
    const destroyed = [
      "roast",
      "poster",
      "refund",
      "faceid",
      "settlement",
      "complete",
    ].includes(s.stage);
    setup.cash.visible = !destroyed && s.phase === "RESOLVE";
    const t = destroying ? Math.min(1, elapsed / 0.6) : 0;
    setup.dissolve.value = t;
    setup.cash.position.copy(setup.target);
    setup.cash.position.y -= 0.12;
    setup.cash.position.lerp(new Vector3(2.15, 1.4, -0.5), t);
    const refund = ["refund", "faceid", "settlement", "complete"].includes(
      s.stage,
    );
    setup.small.visible = refund;
    setup.small.position.set(0, 1.16, 0);
    if (refund)
      setup.small.position.lerp(
        new Vector3(-1.15, 1.16, 0.2),
        s.stage === "refund" ? Math.min(1, elapsed / 0.8) : 1,
      );
    setup.poster.visible = [
      "poster",
      "refund",
      "faceid",
      "settlement",
      "complete",
    ].includes(s.stage);
  });
  return (
    <>
      <primitive object={setup.root} dispose={null} />
      <Bills />
      <Effects selection={setup.selection} />
    </>
  );
}
